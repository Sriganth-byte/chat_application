from rest_framework import status, permissions, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from rest_framework import serializers

from .models import Report, AuditLog
from users.models import User


class ReportSerializer(serializers.ModelSerializer):
    reporter_username = serializers.CharField(source='reporter.username', read_only=True)

    class Meta:
        model = Report
        fields = [
            'id', 'reporter', 'reporter_username', 'target_type', 'target_id',
            'reason', 'description', 'status', 'reviewer_note',
            'auto_flagged', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'reporter', 'status', 'reviewed_by', 'reviewer_note', 'auto_flagged', 'created_at', 'updated_at']


class ReportView(APIView):
    """POST /api/reports/ — file a report"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ReportSerializer(data=request.data)
        if serializer.is_valid():
            report = serializer.save(reporter=request.user)
            # Auto-flag if target has 5+ reports
            same_target_count = Report.objects.filter(
                target_type=report.target_type,
                target_id=report.target_id,
                status='pending'
            ).count()
            if same_target_count >= 5:
                Report.objects.filter(
                    target_type=report.target_type,
                    target_id=report.target_id
                ).update(auto_flagged=True)
            return Response(ReportSerializer(report).data, status=201)
        return Response(serializer.errors, status=400)


class MyReportsView(generics.ListAPIView):
    """GET /api/reports/mine/ — user's own reports"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReportSerializer

    def get_queryset(self):
        return Report.objects.filter(reporter=self.request.user)
