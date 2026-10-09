from django.contrib.auth.models import (AbstractBaseUser, BaseUserManager,
                                        PermissionsMixin)
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Необходимо ввести email")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    phone_number = models.CharField(max_length=15, unique=True, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True)
    avatar = models.ImageField(upload_to="users/avatars/", null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"

    def __str__(self):
        return self.email


class Payment(models.Model):
    CASH = "cash"
    TRANSFER = "transfer"
    STRIPE = 'stripe'

    PAYMENT_METHOD_CHOICES = [
        (CASH, "Наличные"),
        (TRANSFER, "Перевод на счет"),
        (STRIPE, 'Stripe'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payments")

    payment_date = models.DateTimeField(auto_now_add=True)

    course = models.ForeignKey(
        "materials.Course",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
    )

    lesson = models.ForeignKey(
        "materials.Lesson", on_delete=models.SET_NULL, null=True, blank=True
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES)

    stripe_session_id = models.CharField(
        max_length=200,
        blank=True,
        null=True,
    )

    stripe_session_status = models.CharField(
        max_length=50,
        blank=True,
        null=True,
    )

    payment_link = models.URLField(
        max_length=500,
        blank=True,
        null=True,
    )

    stripe_product_id = models.CharField(max_length=200, blank=True, null=True)

    stripe_price_id = models.CharField(max_length=200, blank=True, null=True)

    stripe_payment_status = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.user.email}: {self.amount}"
