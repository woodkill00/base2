import type { Context } from 'react';
export interface ScrollTarget {
  element: HTMLElement | null;
  metrics(): {
    top: number;
    height: number;
    max: number;
    progress: number;
    canAscend: boolean;
    canDescend: boolean;
  };
  scrollTo(_top: number, _behavior?: 'auto' | 'smooth' | 'instant'): void;
  move(_direction: number): void;
  edge(_start: boolean): void;
  align(
    _node: Element,
    _behavior?: 'auto' | 'smooth' | 'instant',
    _options?: { header?: Element | null; scrollMargin?: boolean }
  ): void;
  subscribe(_callback: () => void): () => void;
  lock(): () => void;
}
export function createScrollTarget(
  _element?: HTMLElement | null,
  _headerInset?: () => number
): ScrollTarget;
export const ScrollTargetContext: Context<ScrollTarget | null>;
export function useScrollTargetLock(_active: boolean, _lockDocument?: boolean): void;
export function ScrollTargetLock(_props: { active: boolean }): null;

export function useScrollTargetHistory(
  _key: string,
  _navigationType: string,
  _target: ScrollTarget,
  _ready: boolean,
  _ownsEntry?: () => boolean
): boolean;
