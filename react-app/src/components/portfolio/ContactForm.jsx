import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { fadeUpBlur } from '../../lib/motion';
import GlassCard from '../glass/GlassCard';
import GlassInput from '../glass/GlassInput';
import GlassButton from '../glass/GlassButton';

const ContactForm = () => {
  const [form, setForm] = useState({ name: '', email: '', message: '' });
  const [error, setError] = useState('');
  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });
  const onSubmit = (e) => {
    e.preventDefault();
    if (!form.email || !form.message) {
      setError('Email and message are required');
      return;
    }
    setError('');
    // no-op submit
  };

  return (
    <section aria-labelledby="contact-title" style={styles.section}>
      <motion.div
        initial={fadeUpBlur.initial}
        animate={fadeUpBlur.animate}
        transition={fadeUpBlur.transition}
      >
        <h2 id="contact-title" style={styles.title}>
          Contact
        </h2>
        <GlassCard>
          <form onSubmit={onSubmit} style={styles.form}>
            <GlassInput
              id="c-name"
              name="name"
              type="text"
              value={form.name}
              onChange={onChange}
              placeholder="Your name"
            />
            <GlassInput
              id="c-email"
              name="email"
              type="email"
              value={form.email}
              onChange={onChange}
              placeholder="Your email"
              ariaInvalid={error ? 'true' : 'false'}
            />
            <div className="glass" style={styles.textareaWrap}>
              <label htmlFor="c-message" className="glass-input-label">
                Message
              </label>
              <textarea
                id="c-message"
                name="message"
                value={form.message}
                onChange={onChange}
                placeholder="Tell me about your project…"
                style={styles.textarea}
                aria-invalid={error ? 'true' : 'false'}
              />
              {error ? (
                <div className="glass-input-error" role="alert">
                  {error}
                </div>
              ) : null}
            </div>
            <div
              style={{
                display: 'flex',
                gap: '0.75rem',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <SocialOrbs />
              <GlassButton type="submit" variant="primary" className="glass-pill">
                Send
              </GlassButton>
            </div>
          </form>
        </GlassCard>
      </motion.div>
    </section>
  );
};

const SocialOrbs = () => (
  <div aria-label="Social links" style={{ display: 'flex', gap: '0.5rem' }}>
    {[
      { label: 'Twitter', icon: '🐦', href: '#' },
      { label: 'GitHub', icon: '💻', href: '#' },
      { label: 'LinkedIn', icon: '🔗', href: '#' },
    ].map((s) => (
      <a
        key={s.label}
        href={s.href}
        aria-label={s.label}
        className="glass glass-pill"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '2.25rem',
          height: '2.25rem',
        }}
      >
        <span role="img" aria-label={s.label}>
          {s.icon}
        </span>
      </a>
    ))}
  </div>
);

const styles = {
  section: { padding: 'var(--space) 1rem' },
  title: { textAlign: 'center', marginBottom: 'var(--space)' },
  form: { display: 'grid', gap: '0.75rem' },
  textareaWrap: {
    display: 'grid',
    gap: '0.5rem',
    borderRadius: 'var(--radius)',
    padding: '0.5rem',
  },
  textarea: {
    minHeight: 'clamp(120px, 20vw, 180px)',
    border: '1px solid var(--glass-border)',
    borderRadius: '8px',
    padding: '8px',
    background: 'transparent',
    color: 'inherit',
  },
};

export default ContactForm;
