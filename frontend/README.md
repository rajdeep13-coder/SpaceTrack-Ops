# SpaceTrackOps Frontend

Real-time satellite tracking, orbit propagation, and conjunction detection dashboard.

## Tech Stack

- **Next.js 16** with App Router
- **React 19** with TypeScript
- **Tailwind CSS 4** for styling
- **react-globe.gl** for 3D Earth visualization

## Getting Started

```bash
# Install dependencies
npm install

# Configure API endpoint (optional, defaults to http://127.0.0.1:8000)
cp .env.example .env.local

# Start development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the dashboard.

## Project Structure

```
src/app/
├── page.tsx              # Main dashboard page
├── layout.tsx            # Root layout with fonts and metadata
├── globals.css           # Global styles and theme
├── types.ts              # Shared TypeScript interfaces
├── config.ts             # Configuration constants
├── hooks/                # Custom React hooks
│   ├── useBackendStatus  # Backend health and system status polling
│   ├── useConjunctions   # Conjunction event fetching and filtering
│   ├── useAIAnalysis     # AI risk analysis requests
│   ├── useSatelliteSearch # Debounced satellite search
│   ├── useSatellitePosition # Live position polling
│   └── useActions        # Fetch/detect trigger actions
├── components/
│   ├── GlobeView.tsx     # 3D globe with satellite rendering
│   └── ui/               # Reusable UI primitives
│       ├── GlassPanel    # Glassmorphism container
│       ├── RiskPill      # Risk level badge
│       ├── Dot           # Pulsing status indicator
│       └── StatRow       # Key-value stat display
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://127.0.0.1:8000` | Backend API base URL |
