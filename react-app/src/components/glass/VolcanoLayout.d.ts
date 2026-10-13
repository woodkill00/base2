import type { ReactNode } from 'react';

export default function VolcanoLayout(props: {
  children?: ReactNode;
  headerTitle?: string;
  contextSlot?: ReactNode;
  footerSlot?: ReactNode;
}): ReactNode;
