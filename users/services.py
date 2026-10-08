import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_API_KEY

def create_stripe_product(name):
    product = stripe.Product.create(
        name=name,
    )

    return product

def create_stripe_price(product_id, amount):
    price = stripe.Price.create(
        currency='rub',
        unit_amount=int(amount*100),
        product=product_id,
    )

    return price

def create_stripe_session(price_id):
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[
            {
                'price': price_id,
                'quantity': 1,
            }
        ],
        mode='payment',
        success_url='http://localhost:8000/api/payment/success/',
        cancel_url='http://localhost:8000/api/payment/cancel/',
    )

    return session

def retrieve_stripe_session(session_id):
    session = stripe.checkout.Session.retrieve(session_id,)

    return session