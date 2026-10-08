import stripe

from django.shortcuts import get_object_or_404
from django.db import transaction
from django.http import HttpResponse

from drf_spectacular.utils import extend_schema, OpenApiResponse

from rest_framework import generics, serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import APIException

from .models import Payment, User
from .permissions import IsSelf
from .serializers import (PaymentSerializer, UserRegistrationSerializer,
                          UserSerializer)
from .services import(create_stripe_price,
create_stripe_product,
create_stripe_session,
retrieve_stripe_session,
)


class PaymentErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()

class StripeStatusErrorSerializer(serializers.Serializer):
    error = serializers.CharField()

class PaymentStatusSerializer(serializers.Serializer):
    payment_id = serializers.IntegerField()
    session_id = serializers.CharField()
    status = serializers.CharField()
    payment_status = serializers.CharField()

class UserRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticated, IsSelf]

        return [permission() for permission in permission_classes]


class StripePaymentError(APIException):
    status_code = 502
    default_detail = 'Unable to create Stripe Session'
    default_code = 'stripe_payment_error'


class PaymentListAPIView(generics.ListCreateAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    filterset_fields = ["course", "lesson", "payment_method"]
    ordering_fields = ["payment_date"]
    ordering = ["payment_date"]

    def get_queryset(self):
        return Payment.objects.filter(
            user=self.request.user,
        )

    @extend_schema(
        description=(
                "Создает платеж и автоматически создает "
                "Product, Price и Checkout Session в Stripe. "
                "Возвращает данные платежа и ссылку на оплату."
        ),
        request=PaymentSerializer,
        responses={
            201: PaymentSerializer,
            400: OpenApiResponse(
                description="Некорректные данные платежа.",
            ),
            401: OpenApiResponse(
                response=PaymentErrorSerializer,
                description="Пользователь не авторизован.",
            ),
            502: OpenApiResponse(
                response=PaymentErrorSerializer,
                description="Ошибка Stripe при создании платежа.",
            ),
        },
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        with transaction.atomic():
            payment = serializer.save(user=self.request.user)

            if payment.course:
                product_name = payment.course.title
            elif payment.lesson:
                product_name = payment.lesson.title
            else:
                product_name = 'LMS Payment'

            try:
                product = create_stripe_product(product_name)
                price = create_stripe_price(product.id, payment.amount)

                session = create_stripe_session(price.id)

            except stripe.error.StripeError as e:
                raise StripePaymentError() from e

            payment.stripe_product_id = product.id
            payment.stripe_price_id = price.id
            payment.stripe_session_id = session.id
            payment.payment_link = session.url
            payment.stripe_payment_status = session.payment_status
            payment.stripe_session_status = session.status

            payment.save(
                update_fields=[
                    'stripe_product_id',
                    'stripe_price_id',
                    "stripe_session_id",
                    "payment_link",
                    'stripe_payment_status',
                    'stripe_session_status',
                ]
            )

class PaymentStatusAPIView(APIView):

    @extend_schema(
        description=(
                "Получает актуальный статус платежной сессии "
                "Stripe для платежа текущего пользователя. "
                "Синхронизирует статус с базой данных."
        ),
        responses={
            200: PaymentStatusSerializer,
            400: OpenApiResponse(
                response=StripeStatusErrorSerializer,
                description="Отсутствует или некорректен Stripe Session ID.",
            ),
            401: OpenApiResponse(
                response=PaymentErrorSerializer,
                description="Пользователь не авторизован.",
            ),
            404: OpenApiResponse(
                response=PaymentErrorSerializer,
                description="Платеж не найден или принадлежит другому пользователю.",
            ),
            502: OpenApiResponse(
                response=StripeStatusErrorSerializer,
                description="Ошибка Stripe при получении статуса.",
            ),
        },
    )
    def get(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk, user=request.user,)

        if not payment.stripe_session_id:
            return Response(
                {'error': 'Payment has no Stripe session.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            session = retrieve_stripe_session(payment.stripe_session_id)
        except stripe.error.InvalidRequestError:
            return Response(
                {'error': 'Stripe session does not exist.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except stripe.error.StripeError:
            return Response(
                {'error': 'Unable to retrieve Stripe payment status.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        payment.stripe_payment_status = session.payment_status
        payment.stripe_session_status = session.status

        payment.save(
            update_fields=[
                "stripe_payment_status",
                "stripe_session_status",
            ]
        )

        return Response({
            'payment_id': payment.id,
            'session_id': session.id,
            'status': session.status,
            'payment_status': payment.stripe_payment_status,
        })

class UserRegistrationAPIView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

def payment_success(request):
    return HttpResponse('Payment completed. Thank you!')

def payment_cancel(request):
    return HttpResponse('Payment was cancelled.')