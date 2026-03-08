import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="app-shell">
      <header class="app-header">
        <div class="header-content">
          <div class="logo">
            <span class="logo-icon">🏸</span>
            <span class="logo-text">AI Badminton Coach</span>
          </div>
          <nav class="nav-links">
            <a routerLink="/upload" routerLinkActive="active">Upload Video</a>
          </nav>
        </div>
      </header>
      <main class="app-main">
        <router-outlet />
      </main>
      <footer class="app-footer">
        <p>AI Badminton Coach &copy; 2024 — Powered by MediaPipe &amp; Spring Boot</p>
      </footer>
    </div>
  `,
  styles: [`
    .app-shell {
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      background: #0f0f1a;
      color: #e8eaf6;
      font-family: 'Inter', sans-serif;
    }
    .app-header {
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      border-bottom: 1px solid #2d2d5e;
      padding: 0 2rem;
    }
    .header-content {
      max-width: 1200px;
      margin: 0 auto;
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 64px;
    }
    .logo {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    .logo-icon { font-size: 1.5rem; }
    .logo-text {
      font-size: 1.2rem;
      font-weight: 700;
      color: #7c83fd;
    }
    .nav-links a {
      color: #b0bec5;
      text-decoration: none;
      font-size: 0.9rem;
      padding: 0.4rem 1rem;
      border-radius: 6px;
      transition: all 0.2s;
    }
    .nav-links a:hover, .nav-links a.active {
      background: #1e3a5f;
      color: #7c83fd;
    }
    .app-main {
      flex: 1;
      padding: 2rem;
      max-width: 1200px;
      width: 100%;
      margin: 0 auto;
      box-sizing: border-box;
    }
    .app-footer {
      text-align: center;
      padding: 1rem;
      font-size: 0.75rem;
      color: #546e7a;
      border-top: 1px solid #1e1e3a;
    }
  `]
})
export class AppComponent {}
