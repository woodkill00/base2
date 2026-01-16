import { motion } from 'motion/react';

import GlassCard from '../glass/GlassCard';

const defaultSrc =
  'https://images.unsplash.com/photo-1724159465042-f345315d2cd1?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxnbGFzc21vcnBoaXNtJTIwdWklMjBhYnN0cmFjdHxlbnwxfHx8fDE3NjgzNTk5NTJ8MA&ixlib=rb-4.1.0&q=80&w=1080';

const HomeVisual = ({ src = defaultSrc, alt = 'Glassmorphism UI Abstract' }) => {
  return (
    <section
      style={{ padding: 'calc(4rem) calc(max(1rem, calc((100vw - 1200px) / 2))) calc(4rem)' }}
    >
      <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        >
          <GlassCard style={{ padding: 'calc(3rem) calc(2.5rem)', overflow: 'hidden' }}>
            <div className="text-center" style={{ marginBottom: 'calc(2rem)' }}>
              <h2 style={{ fontSize: 'clamp(1.875rem, 4vw, 2.5rem)', marginBottom: 'calc(1rem)' }}>
                Beautiful by Design
              </h2>
              <p className="text-foreground/70 dark:text-foreground/60">
                Experience the perfect blend of aesthetics and functionality
              </p>
            </div>

            <div
              className="relative rounded-[var(--radius-lg)] overflow-hidden backdrop-blur-2xl bg-white/20 dark:bg-black/30 border border-white/30 dark:border-white/20"
              style={{ aspectRatio: '16 / 9' }}
            >
              <img
                src={src}
                alt={alt}
                className="w-full h-full object-cover opacity-80"
                loading="lazy"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent" />
            </div>

            <div className="relative mt-8 grid grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.1, duration: 0.5, ease: 'easeOut' }}
                  className="aspect-square rounded-[var(--radius-lg)] backdrop-blur-2xl bg-white/20 dark:bg-black/30 border border-white/30 dark:border-white/20"
                />
              ))}
            </div>
          </GlassCard>
        </motion.div>
      </div>
    </section>
  );
};

export default HomeVisual;
