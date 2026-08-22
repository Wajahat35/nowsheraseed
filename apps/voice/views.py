import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from .services import process_voice_command, finalize_voice_draft
from .models import VoiceDraftSession

class VoiceProcessView(LoginRequiredMixin, View):
    """Processes incoming speech/text voice commands and manages draft state."""
    def post(self, request):
        try:
            data = json.loads(request.body.decode('utf-8'))
            text = data.get('text', '').strip()
            session_id = data.get('session_id')

            if not text:
                return JsonResponse({'error': 'No text provided.'}, status=400)

            result = process_voice_command(request.user, text, session_id=session_id)
            return JsonResponse(result)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class VoiceApproveView(LoginRequiredMixin, View):
    """Finalizes and creates the database record ONLY after explicit user approval."""
    def post(self, request):
        try:
            data = json.loads(request.body.decode('utf-8'))
            session_id = data.get('session_id')
            session = VoiceDraftSession.objects.filter(id=session_id, user=request.user, status='DRAFT_PENDING').first()

            if not session:
                return JsonResponse({'error': 'No active pending draft session found.'}, status=404)

            doc_num, print_url, err = finalize_voice_draft(session)
            if err:
                return JsonResponse({'error': f"Failed to save document: {err}"}, status=400)

            session.status = 'APPROVED'
            session.save()

            return JsonResponse({
                'status': 'APPROVED',
                'final_doc_number': doc_num,
                'print_url': print_url,
                'response_text': f"Document #{doc_num} save ho gaya hai."
            })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class VoiceCancelView(LoginRequiredMixin, View):
    """Cancels the active draft session."""
    def post(self, request):
        try:
            data = json.loads(request.body.decode('utf-8'))
            session_id = data.get('session_id')
            session = VoiceDraftSession.objects.filter(id=session_id, user=request.user).first()
            if session:
                session.status = 'CANCELLED'
                session.save()
            return JsonResponse({'status': 'CANCELLED', 'response_text': 'Draft cancelled.'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class VoiceSelectChoiceView(LoginRequiredMixin, View):
    """Binds an ambiguous party or seed choice selected by the user."""
    def post(self, request):
        try:
            data = json.loads(request.body.decode('utf-8'))
            session_id = data.get('session_id')
            choice_type = data.get('choice_type') # 'party' or 'seed'
            choice_id = data.get('choice_id')
            choice_name = data.get('choice_name')

            session = VoiceDraftSession.objects.filter(id=session_id, user=request.user, status='DRAFT_PENDING').first()
            if not session:
                return JsonResponse({'error': 'No active pending draft found.'}, status=404)

            draft = session.draft_data
            if choice_type == 'party':
                draft['party_id'] = choice_id
                draft['party_name'] = choice_name
                draft['party_ambiguous'] = []
            elif choice_type == 'seed':
                draft['seed_id'] = choice_id
                draft['seed_name'] = choice_name
                draft['seed_ambiguous'] = []

            # Recalculate totals if needed
            tot_qty = draft.get('quantity', 0) or 0
            u_rate = draft.get('rate', 0) or 0
            draft['total_amount'] = float(tot_qty * u_rate)

            session.draft_data = draft
            session.save()

            return JsonResponse({
                'session_id': session.id,
                'status': 'DRAFT_PENDING',
                'response_text': f"Selected {choice_name}. Draft updated.",
                'draft': draft
            })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
