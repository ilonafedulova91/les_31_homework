from decimal import Decimal

from rest_framework import serializers

from .models import Payment, User


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = ('user', 'stripe_product_id', 'stripe_price_id', 'stripe_session_id', 'payment_link', 'stripe_payment_status', 'stripe_session_status')

    def validate_amount(self, value):
        if value <= Decimal('0'):
            raise serializers.ValidationError('Amount must be greater than zero')
        return value

    def validate(self, attrs):
        course = attrs.get('course')
        lesson = attrs.get('lesson')

        if bool(course) == bool(lesson):
            raise serializers.ValidationError('Select exactly one: course or lesson')

        if attrs.get('payment_method') != Payment.STRIPE:
            raise serializers.ValidationError(
                {
                    'payment_method': ('This endpoint only supports Stripe payments')
                }
            )

        return attrs

class UserSerializer(serializers.ModelSerializer):
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "city",
            "avatar",
            "payments",
        ]
        read_only_fields = ["id", "payments"]

    def to_representation(self, instance):
        data = super().to_representation(instance)

        request = self.context.get("request")

        if request and request.user != instance:
            data.pop("last_name", None)
            data.pop("payments", None)

        return data


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "city",
            "avatar",
            "password",
        ]

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
