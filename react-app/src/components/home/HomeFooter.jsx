import { Github, Twitter, Linkedin, Mail } from 'lucide-react';

const socialLinks = [
  { icon: Github, href: '#github', label: 'GitHub' },
  { icon: Twitter, href: '#twitter', label: 'Twitter' },
  { icon: Linkedin, href: '#linkedin', label: 'LinkedIn' },
  { icon: Mail, href: '#email', label: 'Email' },
];

const footerLinks = [
  {
    title: 'Product',
    links: ['Features', 'Pricing', 'Documentation', 'Changelog'],
  },
  {
    title: 'Company',
    links: ['About', 'Blog', 'Careers', 'Contact'],
  },
  {
    title: 'Legal',
    links: ['Privacy', 'Terms', 'Security', 'Cookies'],
  },
];

const HomeFooter = () => {
  return (
    <footer
      aria-label="Footer"
      className="backdrop-blur-2xl bg-white/20 dark:bg-black/30 border-t border-white/30 dark:border-white/20"
      style={{ marginTop: 'calc(4rem)' }}
    >
      <div style={{ padding: 'calc(3rem) calc(max(1rem, calc((100vw - 1200px) / 2))) calc(2rem)' }}>
        <div
          className="grid gap-8 mb-8"
          style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}
        >
          <div>
            <div className="flex items-center gap-2 mb-4">
              <svg
                width="32"
                height="32"
                viewBox="0 0 32 32"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                className="text-foreground"
                aria-hidden="true"
              >
                <path d="M16 4L4 10L16 16L28 10L16 4Z" fill="currentColor" opacity="0.3" />
                <path
                  d="M4 16L16 22L28 16"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <path
                  d="M4 22L16 28L28 22"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              <span className="text-lg font-medium">SpecKit</span>
            </div>
            <p className="text-sm text-foreground/60 dark:text-foreground/50 mb-4">
              Building the future of design systems with glassmorphism and AI.
            </p>
            <div className="flex gap-3" aria-label="Social">
              {socialLinks.map((social) => {
                const Icon = social.icon;
                return (
                  <a
                    key={social.label}
                    href={social.href}
                    aria-label={social.label}
                    className="p-2 rounded-[var(--radius-lg)] hover:bg-white/30 dark:hover:bg-black/40 transition-all duration-300 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40 dark:focus-visible:ring-white/30 hover:-translate-y-0.5"
                  >
                    <Icon className="w-4 h-4" aria-hidden="true" />
                  </a>
                );
              })}
            </div>
          </div>

          {footerLinks.map((section) => (
            <div key={section.title}>
              <h3 className="font-medium mb-3">{section.title}</h3>
              <ul className="space-y-2">
                {section.links.map((link) => (
                  <li key={link}>
                    <a
                      href={`#${String(link).toLowerCase().replace(/\s+/g, '-')}`}
                      className="text-sm text-foreground/60 dark:text-foreground/50 hover:text-foreground dark:hover:text-foreground/80 transition-colors duration-300 ease-out focus-visible:outline-none focus-visible:underline"
                    >
                      {link}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="pt-6 border-t border-white/20 dark:border-white/10 flex flex-col sm:flex-row justify-between items-center gap-4">
          <p className="text-sm text-foreground/50 dark:text-foreground/40">
            © 2026 SpecKit. All rights reserved.
          </p>
          <div className="flex gap-6">
            <a
              href="#privacy"
              className="text-sm text-foreground/50 dark:text-foreground/40 hover:text-foreground dark:hover:text-foreground/70 transition-colors duration-300 ease-out focus-visible:outline-none focus-visible:underline"
            >
              Privacy Policy
            </a>
            <a
              href="#terms"
              className="text-sm text-foreground/50 dark:text-foreground/40 hover:text-foreground dark:hover:text-foreground/70 transition-colors duration-300 ease-out focus-visible:outline-none focus-visible:underline"
            >
              Terms of Service
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default HomeFooter;
