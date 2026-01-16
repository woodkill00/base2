import { motion } from 'motion/react';
import { Lock, Cpu, Box, TrendingUp } from 'lucide-react';

const values = [
  { icon: Lock, text: 'Privacy First' },
  { icon: Cpu, text: 'AI Native' },
  { icon: Box, text: 'Open Architecture' },
  { icon: TrendingUp, text: 'Built for Scale' },
];

const HomeTrust = () => {
  return (
    <section
      style={{ padding: 'calc(4rem) calc(max(1rem, calc((100vw - 1200px) / 2))) calc(4rem)' }}
    >
      <div
        className="flex flex-wrap justify-center gap-4"
        style={{ maxWidth: '1000px', margin: '0 auto' }}
      >
        {values.map((value, index) => {
          const Icon = value.icon;
          return (
            <motion.div
              key={value.text}
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.1, duration: 0.5, ease: 'easeOut' }}
              className="backdrop-blur-2xl bg-white/25 dark:bg-black/40 border border-white/30 dark:border-white/20 rounded-full shadow-[0_4px_16px_0_rgba(31,38,135,0.1)] dark:shadow-[0_4px_16px_0_rgba(0,0,0,0.3)]"
              style={{ padding: 'calc(0.75rem) calc(1.5rem)' }}
            >
              <div className="flex items-center gap-2">
                <Icon className="w-4 h-4 text-violet-400" aria-hidden="true" />
                <span className="text-sm font-medium">{value.text}</span>
              </div>
            </motion.div>
          );
        })}
      </div>
    </section>
  );
};

export default HomeTrust;
