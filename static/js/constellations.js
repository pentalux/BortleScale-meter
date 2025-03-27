document.addEventListener('DOMContentLoaded', function() {
    const canvas = document.getElementById('starfield');
    const ctx = canvas.getContext('2d');
    
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    
    const starCount = 200;
    const stars = [];
    const constellations = [];
    const constellationCount = 8;
    for (let i = 0; i < starCount; i++) {
        stars.push({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            radius: Math.random() * 1.2 + 0.3,
            alpha: Math.random() * 0.4 + 0.3,
            twinkleSpeed: Math.random() * 0.01 + 0.005
        });
    }

    for (let i = 0; i < constellationCount; i++) {
        const constellationSize = Math.floor(Math.random() * 4) + 4;
        const constellationStars = [];
        
        const baseX = Math.random() * canvas.width;
        const baseY = Math.random() * canvas.height;
        
        for (let j = 0; j < constellationSize; j++) {
            constellationStars.push({
                x: baseX + (Math.random() - 0.5) * 150,
                y: baseY + (Math.random() - 0.5) * 150,
                radius: Math.random() * 1.2 + 0.8,
                alpha: Math.random() * 0.4 + 0.4,
                twinkleSpeed: Math.random() * 0.01 + 0.005
            });
        }
        constellations.push(constellationStars);
    }
    
    function animate() {
        ctx.fillStyle = 'rgba(0, 0, 0, 0.1)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        stars.forEach(star => {
            drawTwinklingStar(star);
        });
        
        constellations.forEach(constellation => {
            constellation.forEach(star => {
                drawTwinklingStar(star);
            });
            
            drawConstellationLines(constellation);
        });
        
        requestAnimationFrame(animate);
    }
    
    function drawTwinklingStar(star) {
        star.alpha += star.twinkleSpeed;
        if (star.alpha > 0.7 || star.alpha < 0.3) {
            star.twinkleSpeed = -star.twinkleSpeed;
        }
        ctx.beginPath();
        ctx.arc(star.x, star.y, star.radius * 2, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 255, 255, ${star.alpha * 0.2})`;
        ctx.fill();
        
        ctx.beginPath();
        ctx.arc(star.x, star.y, star.radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 255, 255, ${star.alpha})`;
        ctx.fill();
    }
    
    function drawConstellationLines(constellation) {
        ctx.strokeStyle = 'rgba(200, 220, 255, 0.2)';
        ctx.lineWidth = 0.8;
        
        for (let i = 0; i < constellation.length - 1; i++) {
            for (let j = i + 1; j < constellation.length; j++) {
                if (Math.random() > 0.6) {
                    ctx.shadowBlur = 5;
                    ctx.shadowColor = 'rgba(200, 220, 255, 0.3)';
                    
                    ctx.beginPath();
                    ctx.moveTo(constellation[i].x, constellation[i].y);
                    ctx.lineTo(constellation[j].x, constellation[j].y);
                    ctx.stroke();
                    
                    ctx.shadowBlur = 0;
                }
            }
        }
    }
    
    animate();
    
    window.addEventListener('resize', function() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    });
});

