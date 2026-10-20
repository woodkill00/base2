import { createContext, useContext } from 'react';

// Presentational layouts can be rendered without authentication. This context
// carries only notice visibility, never credentials, profiles or authority.
export const ReauthenticationNoticeContext = createContext(false);
export const useReauthenticationNotice = () => useContext(ReauthenticationNoticeContext);
