from django.core import mail
from django.core.management import call_command
from django.test import TestCase

from newsletter.models import Campaign, Subscriber
from shop.tests import make_artwork


class NewsletterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_site", verbosity=0)

    def sign_up(self, email="fan@example.com", **extra):
        return self.client.post("/newsletter/subscribe/", {"email": email, **extra})

    def test_double_opt_in(self):
        self.sign_up()
        sub = Subscriber.objects.get()
        self.assertFalse(sub.is_active)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(sub.token, mail.outbox[0].body)
        self.client.get(f"/newsletter/confirm/{sub.token}/")
        sub.refresh_from_db()
        self.assertTrue(sub.is_active)

    def test_honeypot_and_bad_email(self):
        self.sign_up(website="http://spam")
        self.assertEqual(Subscriber.objects.count(), 0)
        self.assertEqual(self.sign_up(email="nope").status_code, 400)

    def test_german_signup_gets_german_mail(self):
        self.client.post("/de/newsletter/subscribe/", {"email": "de@example.com"})
        self.assertIn("Bitte bestätige", mail.outbox[0].subject)

    def test_unsubscribe_needs_a_post(self):
        sub = Subscriber.objects.create(email="a@example.com", confirmed=True)
        self.client.get(sub.unsubscribe_path())
        sub.refresh_from_db()
        self.assertTrue(sub.is_active)  # a mail scanner opening the link must not unsubscribe anyone
        self.client.post(sub.unsubscribe_path())
        sub.refresh_from_db()
        self.assertFalse(sub.is_active)

    def test_campaign_test_and_send(self):
        art = make_artwork("Rooftops", "rooftops")
        active = Subscriber.objects.create(email="yes@example.com", confirmed=True)
        Subscriber.objects.create(email="pending@example.com")
        gone = Subscriber.objects.create(email="gone@example.com", confirmed=True)
        gone.unsubscribe()

        with self.captureOnCommitCallbacks(execute=True):
            campaign = Campaign.objects.create(
                subject="New work", intro="<p>Hello</p>", artwork=art, send_test_to="me@example.com"
            )
        self.assertEqual([m.to for m in mail.outbox], [["me@example.com"]])
        self.assertTrue(mail.outbox[0].subject.startswith("[TEST]"))
        campaign.refresh_from_db()
        self.assertEqual(campaign.send_test_to, "")

        mail.outbox.clear()
        campaign.send_now = True
        with self.captureOnCommitCallbacks(execute=True):
            campaign.save()
        self.assertEqual([m.to for m in mail.outbox], [[active.email]])
        self.assertIn("Rooftops", mail.outbox[0].alternatives[0][0])
        self.assertIn(active.token, mail.outbox[0].body + mail.outbox[0].alternatives[0][0])
        campaign.refresh_from_db()
        self.assertEqual(campaign.sent_count, 1)

        # saving again never sends twice
        mail.outbox.clear()
        campaign.send_now = True
        with self.captureOnCommitCallbacks(execute=True):
            campaign.save()
        self.assertEqual(mail.outbox, [])
