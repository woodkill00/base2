import { useNavigate } from 'react-router-dom';

import GlassHeader from '../components/glass/GlassHeader';
import GlassSidebar from '../components/glass/GlassSidebar';
import HomeHero from '../components/home/HomeHero';
import HomeFeatures from '../components/home/HomeFeatures';
import HomeVisual from '../components/home/HomeVisual';
import HomeTrust from '../components/home/HomeTrust';
import HomeFooter from '../components/home/HomeFooter';

const Home = () => {
  const navigate = useNavigate();

  const handleMenuItemClick = (path) => {
    if (path === '/') {
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }
    navigate(path);
  };

  return (
    <div className="home-page-root relative min-h-screen" data-testid="home-page">
      <div className="gradient-background" />

      <div className="relative z-10">
        <GlassHeader variant="public" title="Home" />
        <GlassSidebar variant="public" onMenuItemClick={handleMenuItemClick} />

        <main>
          <HomeHero onPrimary={() => navigate('/signup')} onSecondary={() => {}} />
          <HomeFeatures />
          <HomeVisual />
          <HomeTrust />
        </main>

        <HomeFooter />
      </div>
    </div>
  );
};
export default Home;
