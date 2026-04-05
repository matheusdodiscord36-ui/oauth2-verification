/**
 * IceX Verify Enterprise - JavaScript Interativo
 * ===============================================
 * Efeitos visuais e interações para o tema IceX
 */

// =============================================================================
// PARTÍCULAS DE FUNDO
// =============================================================================

class ParticleSystem {
    constructor() {
        this.canvas = document.getElementById('particles-canvas');
        if (!this.canvas) return;
        
        this.ctx = this.canvas.getContext('2d');
        this.particles = [];
        this.maxParticles = 50;
        this.connectionDistance = 100;
        this.maxConnections = 3;
        
        this.resize();
        this.init();
        this.animate();
        
        window.addEventListener('resize', () => this.resize());
    }
    
    resize() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
    }
    
    init() {
        this.particles = [];
        for (let i = 0; i < this.maxParticles; i++) {
            this.particles.push({
                x: Math.random() * this.canvas.width,
                y: Math.random() * this.canvas.height,
                vx: (Math.random() - 0.5) * 0.5,
                vy: (Math.random() - 0.5) * 0.5,
                radius: Math.random() * 2 + 1,
                opacity: Math.random() * 0.5 + 0.2
            });
        }
    }
    
    animate() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Atualiza e desenha partículas
        this.particles.forEach((particle, i) => {
            // Atualiza posição
            particle.x += particle.vx;
            particle.y += particle.vy;
            
            // Wrap around
            if (particle.x < 0) particle.x = this.canvas.width;
            if (particle.x > this.canvas.width) particle.x = 0;
            if (particle.y < 0) particle.y = this.canvas.height;
            if (particle.y > this.canvas.height) particle.y = 0;
            
            // Desenha partícula
            this.ctx.beginPath();
            this.ctx.arc(particle.x, particle.y, particle.radius, 0, Math.PI * 2);
            this.ctx.fillStyle = `rgba(0, 212, 255, ${particle.opacity})`;
            this.ctx.fill();
            
            // Conecta partículas próximas
            let connections = 0;
            for (let j = i + 1; j < this.particles.length; j++) {
                if (connections >= this.maxConnections) break;
                
                const other = this.particles[j];
                const dx = particle.x - other.x;
                const dy = particle.y - other.y;
                const distance = Math.sqrt(dx * dx + dy * dy);
                
                if (distance < this.connectionDistance) {
                    const opacity = (1 - distance / this.connectionDistance) * 0.2;
                    this.ctx.beginPath();
                    this.ctx.moveTo(particle.x, particle.y);
                    this.ctx.lineTo(other.x, other.y);
                    this.ctx.strokeStyle = `rgba(0, 212, 255, ${opacity})`;
                    this.ctx.lineWidth = 0.5;
                    this.ctx.stroke();
                    connections++;
                }
            }
        });
        
        requestAnimationFrame(() => this.animate());
    }
}

// =============================================================================
// EFEITOS DE INTERAÇÃO
// =============================================================================

class InteractionEffects {
    constructor() {
        this.initCardTilt();
        this.initButtonEffects();
        this.initSmoothScroll();
    }
    
    // Efeito de tilt no card
    initCardTilt() {
        const card = document.querySelector('.verify-card');
        if (!card) return;
        
        // Apenas em dispositivos não-touch
        if (window.matchMedia('(pointer: coarse)').matches) return;
        
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            
            const rotateX = (y - centerY) / 20;
            const rotateY = (centerX - x) / 20;
            
            card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
        });
        
        card.addEventListener('mouseleave', () => {
            card.style.transform = 'perspective(1000px) rotateX(0) rotateY(0)';
        });
    }
    
    // Efeitos nos botões
    initButtonEffects() {
        const buttons = document.querySelectorAll('.verify-btn, .back-btn, .home-btn');
        
        buttons.forEach(btn => {
            btn.addEventListener('mouseenter', () => {
                btn.style.transition = 'all 0.3s ease';
            });
            
            // Efeito de ripple no click
            btn.addEventListener('click', (e) => {
                const ripple = document.createElement('span');
                const rect = btn.getBoundingClientRect();
                const size = Math.max(rect.width, rect.height);
                
                ripple.style.cssText = `
                    position: absolute;
                    width: ${size}px;
                    height: ${size}px;
                    left: ${e.clientX - rect.left - size / 2}px;
                    top: ${e.clientY - rect.top - size / 2}px;
                    background: rgba(255, 255, 255, 0.3);
                    border-radius: 50%;
                    transform: scale(0);
                    animation: rippleEffect 0.6s ease-out;
                    pointer-events: none;
                `;
                
                btn.style.position = 'relative';
                btn.style.overflow = 'hidden';
                btn.appendChild(ripple);
                
                setTimeout(() => ripple.remove(), 600);
            });
        });
        
        // Adiciona keyframes do ripple
        const style = document.createElement('style');
        style.textContent = `
            @keyframes rippleEffect {
                to {
                    transform: scale(2);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    // Scroll suave
    initSmoothScroll() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth' });
                }
            });
        });
    }
}

// =============================================================================
// UTILITÁRIOS
// =============================================================================

const Utils = {
    // Debounce para eventos
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    // Throttle para eventos
    throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },
    
    // Animação de contador
    animateCounter(element, target, duration = 2000) {
        let start = 0;
        const increment = target / (duration / 16);
        
        const update = () => {
            start += increment;
            if (start < target) {
                element.textContent = Math.floor(start);
                requestAnimationFrame(update);
            } else {
                element.textContent = target;
            }
        };
        
        update();
    },
    
    // Detecta preferência de redução de movimento
    prefersReducedMotion() {
        return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }
};

// =============================================================================
// INICIALIZAÇÃO
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Inicializa sistema de partículas (se não preferir redução de movimento)
    if (!Utils.prefersReducedMotion()) {
        new ParticleSystem();
    }
    
    // Inicializa efeitos de interação
    new InteractionEffects();
    
    // Adiciona classe de carregamento completo
    document.body.classList.add('loaded');
    
    // Log de inicialização
    console.log('%c❄️ IceX Verify Enterprise', 'color: #00d4ff; font-size: 20px; font-weight: bold;');
    console.log('%cSistema de verificação inicializado', 'color: #a0a0b0;');
});

// =============================================================================
// EXPORTAÇÕES
// =============================================================================

window.IceX = {
    ParticleSystem,
    InteractionEffects,
    Utils
};
  
