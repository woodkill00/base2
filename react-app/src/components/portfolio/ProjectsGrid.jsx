import { Eye, Gauge, GitPullRequest, RotateCcw, ServerCog, TestTube2 } from 'lucide-react';

const modules = [
  {
    icon: GitPullRequest,
    title: 'Branch workstream',
    detail: 'Agents work against isolated feature branches with push approval and review summaries.',
    tags: ['feature branch', 'review', 'rollback'],
  },
  {
    icon: ServerCog,
    title: 'Staging dev-site loop',
    detail: 'Disposable DigitalOcean staging targets can be created, tested, updated, and destroyed.',
    tags: ['staging certs', 'health checks', 'site update'],
  },
  {
    icon: Eye,
    title: 'Visual proof',
    detail: 'Desktop, tablet, and phone captures are compared against the requested design behavior.',
    tags: ['screenshots', 'responsive', 'design QA'],
  },
  {
    icon: TestTube2,
    title: 'CI/CD proof bundle',
    detail: 'Docker install, unit tests, build, smoke, and live readiness results stay tied to the run.',
    tags: ['docker', 'tests', 'build'],
  },
  {
    icon: Gauge,
    title: 'Capacity guardrails',
    detail: 'Heavy steps are scheduled so Woody, OpenClaw, Vaultwarden, and Discord stay hot.',
    tags: ['Pi capacity', 'cooldown', 'always hot'],
  },
  {
    icon: RotateCcw,
    title: 'Failure recovery',
    detail: 'Failed builds capture logs, roll back the site, and report the next fixable action.',
    tags: ['rollback', 'diagnostics', 'retryable'],
  },
];

const ProjectsGrid = () => (
  <section
    id="base2-thermal-security"
    className="base2-integrated-section base2-integrated-projects"
    data-testid="base2-projects-section"
  >
    <div className="base2-integrated-copy">
      <span className="base2-section-kicker">Operational modules</span>
      <h2>The page below the hero now belongs to the same system.</h2>
      <p>
        These cards replace the generic portfolio samples with Base2-specific workflows the team
        actually uses when it plans, changes, deploys, checks, and reports on a repo.
      </p>
    </div>
    <div className="base2-module-grid">
      {modules.map(({ icon: Icon, title, detail, tags }) => (
        <article className="base2-module-card" key={title}>
          <div className="base2-module-icon">
            <Icon aria-hidden="true" />
          </div>
          <h3>{title}</h3>
          <p>{detail}</p>
          <div className="base2-module-tags" aria-label={`${title} tags`}>
            {tags.map((tag) => (
              <span key={tag}>{tag}</span>
            ))}
          </div>
        </article>
      ))}
    </div>
  </section>
);

export default ProjectsGrid;
