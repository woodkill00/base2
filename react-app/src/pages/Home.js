import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import GlassHeader from '../components/glass/GlassHeader';
import AppShell from '../components/glass/AppShell';
import { layoutPreviewEnabled } from '../config/layoutPolicy';
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
import { localizedPath } from '../services/privacyRuntime';

const homeCopy = {
  en: {
    title: 'Home',
    shared: 'Link shared.',
    copied: 'Link copied to clipboard.',
    copyPrompt: 'Copy this link',
    copyManually: 'The manual copy dialog was closed.',
  },
  de: {
    title: 'Startseite',
    shared: 'Link geteilt.',
    copied: 'Link in die Zwischenablage kopiert.',
    copyPrompt: 'Diesen Link kopieren',
    copyManually: 'Der Dialog zum manuellen Kopieren wurde geschlossen.',
  },
  ar: {
    title: 'الرئيسية',
    shared: 'تمت مشاركة الرابط.',
    copied: 'تم نسخ الرابط إلى الحافظة.',
    copyPrompt: 'انسخ هذا الرابط',
    copyManually: 'تم إغلاق مربع حوار النسخ اليدوي.',
  },
};

const Home = ({ locale = siteManifest.defaultLocale }) => {
  const navigate = useNavigate();
  const copy = homeCopy[locale] || homeCopy.en;
  const [shareStatus, setShareStatus] = useState('');

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

  const handleUtilityAction = async (action) => {
    if (action === 'security') {
      handleMenuItemClick('security');
      return;
    }
    if (action === 'search') {
      navigate(localizedPath('/search', locale, siteManifest));
      return;
    }
    if (action !== 'share') return;

    setShareStatus('');
    const shareDetails = { title: document.title, url: window.location.href };
    if (typeof window.navigator.share === 'function') {
      try {
        await window.navigator.share(shareDetails);
        setShareStatus(copy.shared);
        return;
      } catch (error) {
        if (error?.name === 'AbortError') return;
      }
    }
    if (typeof window.navigator.clipboard?.writeText === 'function') {
      try {
        await window.navigator.clipboard.writeText(shareDetails.url);
        setShareStatus(copy.copied);
        return;
      } catch {
        // A visible copy fallback below prevents a silent clipboard failure.
      }
    }
    window.prompt(copy.copyPrompt, shareDetails.url);
    setShareStatus(copy.copyManually);
  };

  const content = (
    <>
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
    </>
  );
  if (layoutPreviewEnabled)
    return (
      <div className="home-page-root" data-testid="home-page">
        <AppShell
          layoutRoute="/"
          headerTitle={copy.title}
          contextSlot={
            <>
              <p>Explore this page</p>
              {['home', 'features', 'command', 'security', 'contact'].map((section) => (
                <button key={section} onClick={() => handleMenuItemClick(section)}>
                  {section[0].toUpperCase() + section.slice(1)}
                </button>
              ))}
              <button onClick={() => handleUtilityAction('share')}>Share this page</button>
              {shareStatus ? (
                <p role="status" data-testid="home-share-status">
                  {shareStatus}
                </p>
              ) : null}
            </>
          }
        >
          {content}
        </AppShell>
      </div>
    );
  return (
    <div className="home-page-root relative min-h-screen" data-testid="home-page">
      <div className="gradient-background" />

      <div className="relative z-10">
        <GlassHeader variant="public" title={copy.title} />
        {shareStatus ? (
          <p
            className="home-share-status"
            role="status"
            aria-live="polite"
            data-testid="home-share-status"
          >
            {shareStatus}
          </p>
        ) : null}
        <HomeObsidianNavigation
          onNavigate={handleMenuItemClick}
          onUtilityAction={handleUtilityAction}
          locale={locale}
        />

        <main>{content}</main>

        <HomeFooter />
      </div>
    </div>
  );
};
export default Home;
