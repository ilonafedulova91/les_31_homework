from rest_framework import serializers

from .models import Course, Lesson, Subscription
from .validators import validate_youtube_url


class LessonSerializer(serializers.ModelSerializer):
    video_url = serializers.URLField(validators=[validate_youtube_url])

    class Meta:
        model = Lesson
        fields = "__all__"
        read_only_fields = ["owner"]


class CourseSerializer(serializers.ModelSerializer):
    lesson_count = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()
    lessons = LessonSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "preview",
            "description",
            "lesson_count",
            "is_subscribed",
            "lessons",
        ]

    def get_lesson_count(self, obj) -> int:
        return obj.lessons.count()

    def get_is_subscribed(self, obj) -> bool:
        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return False

        return Subscription.objects.filter(
            user=request.user,
            course=obj,
        ).exists()


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = "__all__"
        read_only_fields = ["user"]


class SubscriptionRequestSerializer(serializers.Serializer):
    course_id = serializers.IntegerField(min_value=1)


class SubscriptionResponseSerializer(serializers.Serializer):
    message = serializers.CharField()