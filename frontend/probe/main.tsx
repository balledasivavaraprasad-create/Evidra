// Build-only dependency probe. This is not the product frontend.
import { createRoot } from 'react-dom/client';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { motion } from 'motion/react';
import { Search } from 'lucide-react';

createRoot(document.getElementById('root')!).render(
  <QueryClientProvider client={new QueryClient()}>
    <BrowserRouter>
      <motion.main initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <h1><Search aria-hidden />Dependency compile probe only</h1>
        <Canvas><mesh><boxGeometry /><meshStandardMaterial /></mesh><ambientLight /><OrbitControls /></Canvas>
      </motion.main>
    </BrowserRouter>
  </QueryClientProvider>,
);
