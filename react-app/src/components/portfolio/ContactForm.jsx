import { useState } from 'react';
import { CheckCircle2, MessageSquare, Send, ShieldCheck } from 'lucide-react';

const ContactForm = () => {
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (event) => {
    event.preventDefault();
    setSubmitted(true);
  };

  return (
    <section
      id="contact"
      className="base2-integrated-section base2-viewport-section base2-integrated-contact"
      data-base2-section-panel="contact"
      data-testid="base2-contact-section"
    >
      <div className="base2-section-shell">
        <div className="base2-integrated-copy">
          <span className="base2-section-kicker">Handoff</span>
          <h2>Keep feedback actionable for the next agent pass.</h2>
          <p>
            Use this surface to describe what still looks wrong, which screen size it affects, and
            what acceptance proof should be attached to the next run.
          </p>
          <div className="base2-contact-proof">
            <span>
              <ShieldCheck aria-hidden="true" /> Secrets redacted
            </span>
            <span>
              <MessageSquare aria-hidden="true" /> Discord report ready
            </span>
            <span>
              <CheckCircle2 aria-hidden="true" /> Staging cert mode
            </span>
          </div>
        </div>
        <form className="base2-feedback-form" onSubmit={handleSubmit}>
          <label>
            Name
            <input name="name" autoComplete="name" placeholder="Project reviewer" />
          </label>
          <label>
            Email
            <input
              name="email"
              type="email"
              autoComplete="email"
              placeholder="reviewer@example.com"
            />
          </label>
          <label>
            Feedback
            <textarea
              name="message"
              rows="5"
              placeholder="Describe the visual or behavior issue the team should fix next."
            />
          </label>
          <button type="submit">
            <Send aria-hidden="true" />
            Send review note
          </button>
          <p className="base2-form-status" role="status">
            {submitted
              ? 'Review note staged for the next team report.'
              : 'No credentials or private data belong in feedback.'}
          </p>
        </form>
      </div>
    </section>
  );
};

export default ContactForm;
