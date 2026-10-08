from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from materials.models import Course
from users.models import Payment, User


class PaymentTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='payment_test@example.com',
            password='test_password',
        )

        self.course = Course.objects.create(
            title='Stripe Test Course',
            description='Course for Stripe tests',
            owner=self.user,
        )

        self.client.force_authenticate(user=self.user)

    @patch('users.views.create_stripe_session')
    @patch('users.views.create_stripe_price')
    @patch('users.views.create_stripe_product')
    def test_payment_create(self,
                            mock_create_product,
                            mock_create_price,
                            mock_create_session):
        mock_create_product.return_value.id = 'prod_test'
        mock_create_price.return_value.id = 'price_test'

        mock_create_session.return_value.id = 'cs_test_123'
        mock_create_session.return_value.url = ('https://checkout.stripe.com/test')
        mock_create_session.return_value.payment_status = 'unpaid'
        mock_create_session.return_value.status = "open"

        url = reverse('payment-list')

        data = {
            'course': self.course.id,
            'amount': '150.00',
            'payment_method': 'stripe',
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        payment = Payment.objects.get()

        self.assertEqual(payment.user, self.user)
        self.assertEqual(payment.stripe_session_id, 'cs_test_123')
        self.assertEqual(payment.payment_link, 'https://checkout.stripe.com/test')
        mock_create_product.assert_called_once_with(self.course.title)
        mock_create_price.assert_called_once_with('prod_test', payment.amount)
        mock_create_session.assert_called_once_with('price_test')

        self.assertEqual(payment.stripe_product_id, 'prod_test')
        self.assertEqual(payment.stripe_price_id, 'price_test')
        self.assertEqual(payment.stripe_payment_status, 'unpaid')
        self.assertEqual(payment.stripe_session_status, "open")

    @patch('users.views.create_stripe_product')
    def test_payment_creation_stripe_error(self, mock_create_product):
        import stripe

        mock_create_product.side_effect = stripe.error.APIConnectionError(
            message='Stripe connection failed'
        )

        url = reverse('payment-list')
        data = {
            'course': self.course.id,
            'amount': '150.00',
            'payment_method': 'stripe',
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(Payment.objects.count(), 0)
        mock_create_product.assert_called_once_with(self.course.title)

    @patch('users.views.retrieve_stripe_session')
    def test_payment_status(self, mock_retrieve_session):
        payment = Payment.objects.create(
            user=self.user,
            course=self.course,
            amount='150.00',
            payment_method='stripe',
            stripe_session_id='cs_test_123',
            payment_link='https://checkout.stripe.com/test'
        )

        mock_retrieve_session.return_value.id = 'cs_test_123'
        mock_retrieve_session.return_value.status = 'complete'
        mock_retrieve_session.return_value.payment_status = 'paid'

        url = reverse('payment-status', args=[payment.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'complete')
        self.assertEqual(response.data['payment_status'], 'paid')
        mock_retrieve_session.assert_called_once_with('cs_test_123')

        payment.refresh_from_db()
        self.assertEqual(payment.stripe_payment_status, 'paid')
        self.assertEqual(payment.stripe_session_status, "complete")

    @patch('users.views.create_stripe_product')
    def test_invalid_payment_data(self, mock_create_product):
        url = reverse('payment-list')

        invalid_payments = [
            {
                'course': self.course.id,
                'amount': '0.00',
                'payment_method': 'stripe',
            },
            {
                'course': self.course.id,
                'amount': '-100.00',
                'payment_method': 'stripe',
            },
            {
                "amount": "1500.00",
                "payment_method": "stripe",
            },
            {
                "course": self.course.id,
                "lesson": 1,
                "amount": "1500.00",
                "payment_method": "stripe",
            },
            {
                "course": self.course.id,
                "amount": "1500.00",
                "payment_method": "cash",
            },
        ]

        for data in invalid_payments:
            with self.subTest(data=data):
                response = self.client.post(
                    url,
                    data,
                    format="json",
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )

        self.assertEqual(Payment.objects.count(), 0)
        mock_create_product.assert_not_called()

    @patch('users.views.retrieve_stripe_session')
    def test_another_user_cannot_check_payment_status(self, mock_retrieve_session):
        payment = Payment.objects.create(
            user=self.user,
            course=self.course,
            amount='150.00',
            payment_method='stripe',
            stripe_session_id='cs_test_123',
            payment_link='https://checkout.stripe.com/test'
        )

        another_user = User.objects.create_user(
            email='another_payment_user@example.com',
            password='test_password',
        )

        self.client.force_authenticate(user=another_user)

        url = reverse('payment-status', args=[payment.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        mock_retrieve_session.assert_not_called()