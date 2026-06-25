import { Activity, GitBranch, ShieldCheck, TerminalSquare } from 'lucide-react';

const operatingPoints = [
  {
    icon: GitBranch,
    label: 'Repo-aware work',
    text: 'Feature branches, review gates, and rollback notes stay attached to every Base2 change.',
  },
  {
    icon: TerminalSquare,
    label: 'Scripted delivery',
    text: 'Build, deploy, and smoke-test steps are visible before the team touches a live target.',
  },
  {
    icon: ShieldCheck,
    label: 'Credential safe',
    text: 'Secrets stay in scoped Vaultwarden references; reports only show redacted proof.',
  },
  {
    icon: Activity,
    label: 'Live health',
    text: 'Capacity, cert mode, service status, and visual checks are tracked during every run.',
  },
];

const About = () => (
  <section
    id="base2-obsidian-ops"
    className="base2-integrated-section base2-viewport-section base2-integrated-about"
    data-base2-section-panel="command"
    data-testid="base2-about-section"
  >
    <div className="base2-integrated-copy">
      <span className="base2-section-kicker">About Base2</span>
      <h2>Project teams that can ship without exposing the controls.</h2>
      <p>
        Base2 keeps the development surface organized around approved branches, scoped secrets,
        staging-first deploys, and readable operational proof. The visual shell should feel like the
        same volcanic command center from the hero all the way through the final handoff.
      </p>
    </div>
    <div className="base2-integrated-grid" aria-label="Base2 operating model">
      {operatingPoints.map(({ icon: Icon, label, text }) => (
        <article className="base2-integrated-card" key={label}>
          <Icon aria-hidden="true" />
          <h3>{label}</h3>
          <p>{text}</p>
        </article>
      ))}
    </div>
  </section>
);

export default About;
