from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags


def _is_enabled(setting_name, default=True):
    return getattr(settings, setting_name, default)


def _send_html_email(*, recipient_email, subject, preheader, heading, intro, highlights=None, footer_note=None):
    if not recipient_email:
        return False, 'Recipient has no email address.'

    highlights = highlights or []
    footer_note = footer_note or 'Sign in to Vashandi to continue the conversation.'

    highlight_html = ''.join(
        f"""
        <tr>
            <td style="padding: 0 0 14px;">
                <div style="border: 1px solid #e9dcc2; border-radius: 14px; background: #fffaf0; padding: 14px 16px;">
                    <div style="font-size: 12px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: #9c7310; margin-bottom: 6px;">{item['label']}</div>
                    <div style="font-size: 15px; line-height: 1.6; color: #17130d;">{item['value']}</div>
                </div>
            </td>
        </tr>
        """
        for item in highlights
    )

    html_body = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{subject}</title>
    </head>
    <body style="margin:0; padding:0; background:#f6f0e3; font-family: Georgia, 'Times New Roman', serif; color:#17130d;">
        <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background:#f6f0e3; padding:32px 12px;">
            <tr>
                <td align="center">
                    <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="max-width:640px; background:#fffdf8; border:1px solid #eddcb5; border-radius:28px; overflow:hidden; box-shadow:0 24px 54px rgba(81, 60, 31, 0.12);">
                        <tr>
                            <td style="padding:28px 32px; background:linear-gradient(145deg, #c7961a, #9c7310); color:#17130d;">
                                <div style="font-size:12px; letter-spacing:0.12em; text-transform:uppercase; font-weight:700; opacity:0.85;">Vashandi</div>
                                <div style="font-size:28px; line-height:1.25; font-weight:700; margin-top:10px;">{heading}</div>
                                <div style="font-size:14px; line-height:1.6; margin-top:10px; opacity:0.9;">{preheader}</div>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding:28px 32px 18px;">
                                <div style="font-size:16px; line-height:1.8; color:#423424; margin-bottom:18px;">{intro}</div>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding:0 32px 12px;">
                                <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
                                    {highlight_html}
                                </table>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding:8px 32px 30px; font-size:14px; line-height:1.7; color:#746754;">
                                {footer_note}
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    text_parts = [heading, '', preheader, '', intro]
    for item in highlights:
        text_parts.extend(['', f"{item['label']}: {item['value']}"])
    text_parts.extend(['', footer_note, '', 'Vashandi'])
    text_body = '\n'.join(text_parts)

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient_email],
    )
    email.attach_alternative(html_body, 'text/html')
    try:
        email.send(fail_silently=False)
        return True, None
    except Exception as exc:
        return False, str(exc)


def send_welcome_email(user):
    if not _is_enabled('SEND_WELCOME_EMAILS', True):
        return False, 'Welcome emails are disabled.'
    return _send_html_email(
        recipient_email=user.email,
        subject='Welcome to Vashandi',
        preheader='Your account has been created and is waiting for verification approval.',
        heading=f"Welcome, {user.display_name}",
        intro='Your Vashandi account has been created successfully and is now pending admin verification.',
        highlights=[
            {'label': 'Role', 'value': user.get_current_role_display()},
            {'label': 'Username', 'value': user.username},
            {'label': 'Verification', 'value': user.get_verification_status_display()},
        ],
        footer_note='You will be able to sign in after your verification documents have been reviewed and approved.'
    )


def send_message_email(message_obj):
    if not _is_enabled('SEND_MESSAGE_EMAILS', True):
        return False, 'Message emails are disabled.'
    subject_context = message_obj.service.title if message_obj.service else (message_obj.job.title if message_obj.job else 'Direct Conversation')
    return _send_html_email(
        recipient_email=message_obj.recipient.email,
        subject=f'New message from {message_obj.sender.display_name}',
        preheader='You have a new platform message waiting for you.',
        heading='New Message Received',
        intro=f"{message_obj.sender.display_name} sent you a new message on Vashandi.",
        highlights=[
            {'label': 'Context', 'value': subject_context},
            {'label': 'Message Preview', 'value': message_obj.content},
        ],
    )


def send_rfq_email(rfq):
    return _send_html_email(
        recipient_email=rfq.provider.email,
        subject=f'New RFQ for {rfq.service.title}',
        preheader='A client wants a quote from you.',
        heading='New RFQ Submitted',
        intro=f"{rfq.client.display_name} sent you a request for quote.",
        highlights=[
            {'label': 'Service', 'value': rfq.service.title},
            {'label': 'RFQ Title', 'value': rfq.title},
            {'label': 'Requirements', 'value': rfq.requirements},
        ],
    )


def send_invoice_email(invoice):
    return _send_html_email(
        recipient_email=invoice.client.email,
        subject=f'New invoice from {invoice.provider.display_name}',
        preheader='A provider has sent you an invoice on Vashandi.',
        heading='New Invoice Ready',
        intro=f"{invoice.provider.display_name} has sent you an invoice.",
        highlights=[
            {'label': 'Invoice', 'value': invoice.title},
            {'label': 'Total', 'value': f'{invoice.client.currency_symbol}{invoice.total_amount} {invoice.client.currency_code}'},
            {'label': 'Due Date', 'value': invoice.due_date or 'Not specified'},
        ],
    )


def send_review_email(review):
    return _send_html_email(
        recipient_email=review.service.provider.email,
        subject='New review received',
        preheader='A client left feedback on your service.',
        heading='New Review Received',
        intro=f"{review.reviewer.display_name} left a new review on your service.",
        highlights=[
            {'label': 'Service', 'value': review.service.title},
            {'label': 'Rating', 'value': f'{review.rating} / 5'},
            {'label': 'Comment', 'value': review.comment},
        ],
    )


def send_status_change_email(job, actor, note=''):
    if not job.assigned_provider or not job.assigned_provider.email:
        return False, 'Assigned provider has no email address.'
    note_value = note or 'No note included.'
    return _send_html_email(
        recipient_email=job.assigned_provider.email,
        subject=f'Job status updated: {job.title}',
        preheader='A client updated the status of your assigned job.',
        heading='Job Status Updated',
        intro=f"{actor.display_name} updated the status of a job you are assigned to.",
        highlights=[
            {'label': 'Job', 'value': job.title},
            {'label': 'New Status', 'value': job.get_status_display()},
            {'label': 'Note', 'value': note_value},
        ],
    )


def send_bid_email(*, recipient, actor, subject, heading, intro, job_title, amount=None, extra_label=None, extra_value=None):
    highlights = [{'label': 'Job', 'value': job_title}]
    if amount is not None:
        highlights.append({'label': 'Amount', 'value': f'{recipient.currency_symbol}{amount} {recipient.currency_code}'})
    if extra_label and extra_value is not None:
        highlights.append({'label': extra_label, 'value': extra_value})
    return _send_html_email(
        recipient_email=recipient.email,
        subject=subject,
        preheader='There is an update on your bid activity.',
        heading=heading,
        intro=intro,
        highlights=highlights,
    )


def send_notification_samples(recipient_email):
    from .models import User, Service, Job, Review, Message, RFQ, Invoice

    client = User(username='client_demo', first_name='Client', last_name='Demo', email=recipient_email, current_role='client')
    provider = User(username='provider_demo', first_name='Provider', last_name='Demo', email=recipient_email, current_role='provider')
    service = Service(provider=provider, category='plumbing', title='Premium Plumbing Service', description='Detailed plumbing support.', price_per_hour=120, experience_years=8)
    job = Job(client=client, assigned_provider=provider, service=service, title='Emergency Leak Repair', category='plumbing', description='Fix a leaking pipe urgently.', budget=300, location='Harare', status='in_progress')
    message = Message(sender=client, recipient=provider, service=service, content='Can you start tomorrow morning?')
    review = Review(service=service, reviewer=client, job=job, rating=5, comment='Excellent communication and clean work.')
    rfq = RFQ(client=client, provider=provider, service=service, title='Quote for bathroom refit', requirements='Please quote a full bathroom pipe replacement.', quantity=1)
    invoice = Invoice(provider=provider, client=client, rfq=rfq, service=service, title='Bathroom refit quotation', scope_of_work='Supply materials and complete installation.', subtotal=450, tax_amount=67.5, total_amount=517.5)

    results = []
    results.append(('welcome', send_welcome_email(client)))
    results.append(('message', send_message_email(message)))
    results.append(('rfq', send_rfq_email(rfq)))
    results.append(('invoice', send_invoice_email(invoice)))
    results.append(('review', send_review_email(review)))
    results.append(('status_change', send_status_change_email(job, client, 'Please prioritise this for this week.')))
    results.append((
        'bid',
        send_bid_email(
            recipient=client,
            actor=provider,
            subject='New bid on Emergency Leak Repair',
            heading='New Bid Received',
            intro='A provider placed a new bid on your job.',
            job_title=job.title,
            amount='275.00',
            extra_label='Timeline',
            extra_value='Within 1 week',
        ),
    ))
    return results
