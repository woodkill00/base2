import GlassHeader from '../glass/GlassHeader';
import HomeFooter from '../home/HomeFooter';

const PublicShell = ({ title, children }) => (
  <div className="home-page-root relative min-h-screen">
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
