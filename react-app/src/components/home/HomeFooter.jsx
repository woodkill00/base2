import { Github, LockKeyhole, RadioTower, ShieldCheck } from 'lucide-react';

const footerLinks = [
  { label: 'Repo workflow', href: '#base2-obsidian-ops' },
  { label: 'Security posture', href: '#base2-thermal-security' },
  { label: 'Review handoff', href: '#contact' },
];

const HomeFooter = () => (
  <footer className="base2-integrated-footer" data-testid="base2-footer" aria-label="Footer">
    <div>
      <span className="base2-footer-mark">Base2</span>
      <p>Volcanic staging shell for managed agent delivery, review, and recovery.</p>
    </div>
    <nav aria-label="Base2 footer">
      {footerLinks.map((link) => (
        <a href={link.href} key={link.href}>{link.label}</a>
      ))}
    </nav>
    <div className="base2-footer-proof" aria-label="Base2 live proof">
      <span><RadioTower aria-hidden="true" /> Live staging</span>
      <span><LockKeyhole aria-hidden="true" /> Vault refs only</span>
      <span><ShieldCheck aria-hidden="true" /> Safe rollback</span>
      <a href="https://github.com/woodkill00/base2" aria-label="Base2 GitHub repository">
        <Github aria-hidden="true" />
      </a>
    </div>
  </footer>
);

export default HomeFooter;
