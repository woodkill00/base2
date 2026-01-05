import React from 'react';

type Props = { theme: 'light' | 'dark'; label?: string; size?: number };

// Inline SVG icon with simple animation for sun/moon
export const SunMoon: React.FC<Props> = ({ theme, label, size = 20 }) => {
  const common = { width: size, height: size };
  const aria = label ?? (theme === 'dark' ? 'moon' : 'sun');
  if (theme === 'dark') {
    return (
      <svg
        {...common}
        role="img"
        aria-label={aria}
        viewBox="0 0 24 24"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"
          fill="currentColor"
        >
          <animate attributeName="opacity" values="0.8;1;0.8" dur="2s" repeatCount="indefinite" />
        </path>
      </svg>
    );
  }
  return (
    <svg
      {...common}
      role="img"
      aria-label={aria}
      viewBox="0 0 24 24"
      xmlns="http://www.w3.org/2000/svg"
    >
      <circle cx="12" cy="12" r="5" fill="currentColor">
        <animate attributeName="r" values="4.8;5.2;4.8" dur="2s" repeatCount="indefinite" />
      </circle>
      <g fill="currentColor">
        <circle cx="12" cy="2" r="1" />
        <circle cx="12" cy="22" r="1" />
        <circle cx="2" cy="12" r="1" />
        <circle cx="22" cy="12" r="1" />
        <circle cx="4.5" cy="4.5" r="1" />
        <circle cx="19.5" cy="4.5" r="1" />
        <circle cx="4.5" cy="19.5" r="1" />
        <circle cx="19.5" cy="19.5" r="1" />
      </g>
    </svg>
  );
};

export default SunMoon;
