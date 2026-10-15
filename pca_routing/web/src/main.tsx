import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, NavLink, Route, Routes } from "react-router-dom";
import Demo from "./pages/Demo";
import Why from "./pages/Why";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <header className="top">
        <strong>PCA Routing · RNP backbone</strong>
        <nav>
          <NavLink to="/" end>Demo</NavLink>
          <NavLink to="/why">Why coordinate?</NavLink>
        </nav>
      </header>
      <Routes>
        <Route path="/" element={<Demo />} />
        <Route path="/why" element={<Why />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
);
