import React from 'react';
import { motion } from 'framer-motion';
import { fadeUpBlur } from '../../lib/motion';
import ProjectCard from './ProjectCard';

const sample = [
  {
    title: 'Glass UI Kit',
    description: 'Reusable glassmorphism components.',
    tech: ['React', 'Tailwind'],
  },
  { title: 'Motion Gallery', description: 'Framer Motion showcase.', tech: ['Framer Motion'] },
  { title: 'A11y Toolkit', description: 'Accessible patterns and helpers.', tech: ['RTL', 'Axe'] },
];

const ProjectsGrid = () => {
  return (
    <section aria-labelledby="projects-title" style={styles.section}>
      <motion.div
        initial={fadeUpBlur.initial}
        animate={fadeUpBlur.animate}
        transition={fadeUpBlur.transition}
      >
        <h2 id="projects-title" style={styles.title}>
          Projects
        </h2>
        <div style={styles.grid}>
          {sample.map((p) => (
            <ProjectCard key={p.title} {...p} />
          ))}
        </div>
      </motion.div>
    </section>
  );
};

const styles = {
  section: { padding: 'var(--space) 1rem' },
  title: { textAlign: 'center', marginBottom: 'var(--space)' },
  grid: {
    display: 'grid',
    gap: 'var(--space)',
    gridTemplateColumns: 'repeat(auto-fit, minmax(clamp(260px, 30vw, 360px), 1fr))',
  },
};

export default ProjectsGrid;
