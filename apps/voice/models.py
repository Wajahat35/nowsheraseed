from django.db import models
from django.conf import settings

class VoiceDraftSession(models.Model):
    DOC_TYPES = [
        ('PURCHASE_INVOICE', 'Purchase Invoice'),
        ('SALES_INVOICE', 'Sales Invoice'),
        ('GATE_PASS', 'Gate Pass'),
        ('TRADING_SALES', 'Seeds Trading Sales Invoice'),
        ('TRADING_PURCHASE', 'Seeds Trading Purchase Invoice'),
        ('TRADING_GATEPASS', 'Seeds Trading Gate Pass'),
    ]

    STATUS_CHOICES = [
        ('DRAFT_PENDING', 'Draft Pending Approval'),
        ('APPROVED', 'Approved & Saved'),
        ('CANCELLED', 'Cancelled'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='voice_draft_sessions')
    doc_type = models.CharField(max_length=30, choices=DOC_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT_PENDING')
    
    draft_data = models.JSONField(default=dict, help_text="Structured draft metadata and line items")
    transcript_history = models.JSONField(default=list, help_text="Chronological conversation transcript")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Voice Draft #{self.id} ({self.get_doc_type_display()}) - {self.user.username} [{self.status}]"
