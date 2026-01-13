import React from 'react';

function SectionContainer({ id, className = '', style = {}, children }) {
  return (
    <section id={id} className={`section-space ${className}`} style={style}>
      <div className="mx-auto" style={{ maxWidth: 'min(1200px, 92vw)' }}>
        {children}
      </div>
    </section>
  );
}

export default SectionContainer;
