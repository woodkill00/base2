import { useNavigate } from 'react-router-dom';

import GlassHeader from '../components/glass/GlassHeader';
import HomeHero from '../components/home/HomeHero';
import HomeObsidianNavigation from '../components/home/HomeObsidianNavigation';
import HomeObsidianOps from '../components/home/HomeObsidianOps';
import HomeThermalSecurity from '../components/home/HomeThermalSecurity';
import HomeFeatures from '../components/home/HomeFeatures';
import HomeVisual from '../components/home/HomeVisual';
import HomeTrust from '../components/home/HomeTrust';
import HomeFooter from '../components/home/HomeFooter';
import About from '../components/portfolio/About';
import ContactForm from '../components/portfolio/ContactForm';
import ProjectsGrid from '../components/portfolio/ProjectsGrid';
import { siteManifest } from '../config/siteRuntime';

const Home = () => {
  const navigate = useNavigate();

  const handleMenuItemClick = (sectionId) => {
    if (sectionId === 'home') {
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    const targetBySection = {
      features: 'features',
      command: 'base2-obsidian-ops',
      security: 'base2-thermal-security',
      contact: 'contact',
    };
    const target = document.getElementById(targetBySection[sectionId]);
    target?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <div className="home-page-root relative min-h-screen" data-testid="home-page">
      <div className="gradient-background" />

      <div className="relative z-10">
        <GlassHeader variant="public" title="Home" />
        <HomeObsidianNavigation onNavigate={handleMenuItemClick} />

        <main>
          <HomeHero
            onPrimary={() =>
              navigate(
                siteManifest.contact.enabled ? '/contact' : siteManifest.navigation[0]?.path || '/'
              )
            }
            onSecondary={() => navigate(siteManifest.legal.accessibilityPath)}
            onSearch={(query) => navigate(`/search?q=${encodeURIComponent(query)}`)}
          />
          <HomeFeatures />
          <HomeObsidianOps />
          <About />
          <ProjectsGrid />
          <ContactForm />
          <HomeVisual />
          <HomeThermalSecurity />
          <HomeTrust />
        </main>

        <HomeFooter />
      </div>
    </div>
  );
};
export default Home;
