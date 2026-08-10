import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { MsalProvider } from '@azure/msal-react'
import './index.css'
import App from './App.tsx'
import { msalInstance, restoreActiveAccount } from './msalInstance'

await msalInstance.initialize()
// Must run after initialize() and before the first render: a reloaded
// session has cached accounts but no active one, and every API call
// reads the active account to attach its bearer token.
restoreActiveAccount(msalInstance)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <MsalProvider instance={msalInstance}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </MsalProvider>
  </StrictMode>,
)
