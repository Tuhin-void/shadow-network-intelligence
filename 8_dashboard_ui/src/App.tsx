import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Investigation from './pages/Investigation';
import Reports from './pages/Reports';
import Search from './pages/Search';

function App() {
  return (
    <div className="min-h-screen bg-gray-100">
      <nav className="bg-gray-800 text-white p-4">
        <div className="container mx-auto flex items-center justify-between">
          <h1 className="text-xl font-bold">Shadow Network Intelligence</h1>
          <div className="flex gap-4">
            <a href="/" className="hover:text-gray-300">Dashboard</a>
            <a href="/search" className="hover:text-gray-300">Search</a>
            <a href="/reports" className="hover:text-gray-300">Reports</a>
          </div>
        </div>
      </nav>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/investigation/:id" element={<Investigation />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/search" element={<Search />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
