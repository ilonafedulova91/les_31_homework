from django.shortcuts import get_object_or_404
from rest_framework import generics, status, viewsets, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from users.permissions import IsModerator, IsOwner

from .models import Course, Lesson, Subscription
from .paginators import CoursePagination, LessonPagination
from .serializers import CourseSerializer, LessonSerializer, SubscriptionRequestSerializer, SubscriptionResponseSerializer


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all().order_by("id")
    serializer_class = CourseSerializer
    pagination_class = CoursePagination

    def get_queryset(self):
        if self.request.user.groups.filter(name="Moderator").exists():
            return Course.objects.all().order_by("id")

        return Course.objects.filter(owner=self.request.user).order_by("id")

    def get_permissions(self):
        if self.action == "list":
            permission_classes = [IsAuthenticated]

        elif self.action in ["retrieve", "update", "partial_update"]:
            permission_classes = [IsAuthenticated, IsModerator | IsOwner]

        elif self.action == "create":
            permission_classes = [IsAuthenticated, ~IsModerator]

        elif self.action == "destroy":
            permission_classes = [IsAuthenticated, ~IsModerator, IsOwner]

        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class LessonListCreateAPIView(generics.ListCreateAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    pagination_class = LessonPagination

    def get_queryset(self):
        if self.request.user.groups.filter(name="Moderator").exists():
            return Lesson.objects.all().order_by("id")

        return Lesson.objects.filter(owner=self.request.user).order_by("id")

    def get_permissions(self):
        if self.request.method == "POST":
            permission_classes = [IsAuthenticated, ~IsModerator]
        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class LessonRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = LessonSerializer

    def get_queryset(self):
        if self.request.user.groups.filter(name="Moderator").exists():
            return Lesson.objects.all()

        return Lesson.objects.filter(owner=self.request.user)

    def get_permissions(self):
        if self.request.method in ["GET", "PUT", "PATCH"]:
            permission_classes = [IsAuthenticated, IsModerator | IsOwner]

        elif self.request.method == "DELETE":
            permission_classes = [IsAuthenticated, ~IsModerator, IsOwner]

        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]


class SubscriptionAPIView(APIView):

    @extend_schema(
        description=(
                "Добавляет подписку на курс или удаляет "
                "существующую подписку текущего пользователя."
        ),
        request=SubscriptionRequestSerializer,
        responses={
            200: OpenApiResponse(
                response=SubscriptionResponseSerializer,
                description="Подписка удалена.",
            ),
            201: OpenApiResponse(
                response=SubscriptionResponseSerializer,
                description="Подписка добавлена.",
            ),
            400: OpenApiResponse(
                description="Некорректный course_id.",
            ),
            401: OpenApiResponse(
                description="Пользователь не авторизован.",
            ),
            404: OpenApiResponse(
                description="Курс не найден.",
            ),
        },
    )

    def post(self, request):
        serializer = SubscriptionRequestSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        course_id = serializer.validated_data["course_id"]

        course = get_object_or_404(Course, pk=course_id)

        subscription = Subscription.objects.filter(
            user=request.user,
            course=course,
        ).first()

        if subscription:
            subscription.delete()
            return Response(
                {"message": "Подписка отменена."},
                status=status.HTTP_200_OK,
            )

        Subscription.objects.create(
            user=request.user,
            course=course,
        )

        return Response(
            {"message": "Подписка добавлена."}, status=status.HTTP_201_CREATED
        )
