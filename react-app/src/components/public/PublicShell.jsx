import GlassHeader from '../glass/GlassHeader';
import HomeFooter from '../home/HomeFooter';
import PageMetadata from './PageMetadata';
import AppShell from '../glass/AppShell';
import { layoutPreviewEnabled } from '../../config/layoutPolicy';

const PublicShell = ({ title, children }) =>
  layoutPreviewEnabled ? (
    <AppShell variant="public" headerTitle={title}>
      <PageMetadata title={title} />
      <div className="public-page-content">{children}</div>
    </AppShell>
  ) : (
    <div className="home-page-root relative min-h-screen" data-experience="base2">
      <PageMetadata title={title} />
      <div className="gradient-background" />
      <div className="relative z-10">
        <GlassHeader variant="public" title={title} />
        <main
          id="main-content"
          tabIndex="-1"
          style={{
            minHeight: '65vh',
            padding: 'clamp(2rem, 6vw, 5rem) max(1rem, calc((100vw - 960px) / 2))',
          }}
        >
          {children}
        </main>
        <HomeFooter />
      </div>
    </div>
  );

export default PublicShell;
