import { useState } from 'react';
import { motion } from 'motion/react';
import { Search, Sparkles } from 'lucide-react';

import GlassCard from '../glass/GlassCard';
import GlassButton from '../glass/GlassButton';
import GlassInput from '../glass/GlassInput';

const HomeHero = ({ onPrimary, onSecondary }) => {
  const [query, setQuery] = useState('');

  return (
    <section
      className="relative flex items-center justify-center"
      style={{
        minHeight: 'calc(100vh - 3.5rem - 1px)',
        padding: 'calc(2rem) calc(max(1rem, calc((100vw - 1200px) / 2)))',
      }}
    >
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: 'easeOut' }}
        style={{ width: 'calc(min(100%, 960px))' }}
      >
        <GlassCard
          className="relative overflow-hidden"
          style={{ padding: 'calc(clamp(3rem, 6vw, 5rem)) calc(clamp(2rem, 5vw, 4rem))' }}
        >
          <motion.div
            className="absolute inset-0 opacity-20 dark:opacity-30"
            style={{
              background:
                'radial-gradient(circle at 50% 0%, rgba(139, 92, 246, 0.4), transparent 50%)',
            }}
            animate={{ opacity: [0.2, 0.4, 0.2] }}
            transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
          />

          <div
            className="relative z-10 flex flex-col items-center text-center"
            style={{ gap: 'calc(1.5rem)' }}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.2, duration: 0.5, ease: 'easeOut' }}
              className="inline-flex items-center gap-2 backdrop-blur-2xl bg-white/25 dark:bg-black/40 border border-white/30 dark:border-white/20 rounded-full px-4 py-2 shadow-[0_4px_16px_0_rgba(31,38,135,0.1)] dark:shadow-[0_4px_16px_0_rgba(0,0,0,0.3)]"
            >
              <Sparkles className="w-4 h-4" aria-hidden="true" />
              <span className="text-sm">AI-Native Architecture</span>
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3, duration: 0.6, ease: 'easeOut' }}
              style={{ fontSize: 'clamp(2rem, 5vw, 3.5rem)', lineHeight: '1.2' }}
            >
              Build Better with
              <br />
              <span className="bg-gradient-to-r from-violet-400 to-fuchsia-400 bg-clip-text text-transparent">
                Glass Design System
              </span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4, duration: 0.6, ease: 'easeOut' }}
              className="text-foreground/70 dark:text-foreground/60 max-w-2xl"
              style={{ fontSize: 'clamp(1rem, 2vw, 1.25rem)' }}
            >
              A premium glassmorphism design system for building modern, AI-powered interfaces with
              React and Tailwind CSS. Fast, accessible, and beautiful.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5, duration: 0.6, ease: 'easeOut' }}
              style={{ width: 'calc(min(100%, 600px))' }}
            >
              <GlassInput
                id="hero-search"
                label={undefined}
                name="heroSearch"
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask anything..."
                icon={<Search className="w-5 h-5" />}
                className="text-lg"
              />
            </motion.div>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.6, duration: 0.6, ease: 'easeOut' }}
              className="flex flex-wrap gap-4 justify-center"
              style={{ marginTop: 'calc(1rem)' }}
            >
              <GlassButton variant="primary" onClick={onPrimary}>
                Get Started
              </GlassButton>
              <GlassButton variant="ghost" onClick={onSecondary}>
                View Documentation
              </GlassButton>
            </motion.div>
          </div>
        </GlassCard>
      </motion.div>
    </section>
  );
};

export default HomeHero;
