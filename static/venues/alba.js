// Alba - Langhe Hills / Piemont (Blueprint Style)
venues.alba = {
    name: 'LANGHE HILLS • ALBA',
    taglineWPC: 'WPC Alba 2026',
    taglinePCL: 'PCL Alba 2026',
    badge: 'Alba',
    svg: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 400" fill="none" stroke="white" stroke-linecap="round" stroke-linejoin="round">' +
        // Hügel Hintergrund
        '<path d="M 0 300 Q 100 260 200 280 Q 350 240 500 260 Q 650 230 800 270" stroke-width="0.8" opacity="0.5"/>' +
        '<path d="M 0 320 Q 150 280 300 300 Q 450 270 600 290 Q 750 260 800 290" stroke-width="0.6" opacity="0.4"/>' +
        // Hügel Vordergrund
        '<path d="M 0 350 Q 100 320 200 340 Q 350 300 500 330 Q 650 290 800 330" stroke-width="1"/>' +
        '<path d="M 0 370 Q 200 340 400 360 Q 600 330 800 360" stroke-width="1.2"/>' +
        // Weinreben-Linien auf Hügeln
        '<path d="M 50 340 L 60 335 L 70 340 L 80 335 L 90 340" stroke-width="0.4" opacity="0.5"/>' +
        '<path d="M 100 335 L 110 330 L 120 335 L 130 330 L 140 335" stroke-width="0.4" opacity="0.5"/>' +
        '<path d="M 550 320 L 560 315 L 570 320 L 580 315 L 590 320" stroke-width="0.4" opacity="0.5"/>' +
        '<path d="M 620 310 L 630 305 L 640 310 L 650 305 L 660 310" stroke-width="0.4" opacity="0.5"/>' +
        // Turm 1 - links
        '<rect x="170" y="180" width="50" height="160" stroke-width="1.2"/>' +
        '<line x1="170" y1="220" x2="220" y2="220" stroke-width="0.5"/>' +
        '<line x1="170" y1="260" x2="220" y2="260" stroke-width="0.5"/>' +
        '<line x1="170" y1="300" x2="220" y2="300" stroke-width="0.5"/>' +
        '<polygon points="170,180 195,120 220,180" stroke-width="1.2" fill="none"/>' +
        '<line x1="195" y1="120" x2="195" y2="100" stroke-width="0.8"/>' +
        // Fenster Turm 1
        '<rect x="185" y="200" width="20" height="15" stroke-width="0.5"/>' +
        '<rect x="185" y="240" width="20" height="15" stroke-width="0.5"/>' +
        '<rect x="185" y="280" width="20" height="15" stroke-width="0.5"/>' +
        // Turm 2 - Mitte (größer)
        '<rect x="370" y="140" width="60" height="200" stroke-width="1.5"/>' +
        '<line x1="370" y1="180" x2="430" y2="180" stroke-width="0.6"/>' +
        '<line x1="370" y1="220" x2="430" y2="220" stroke-width="0.6"/>' +
        '<line x1="370" y1="260" x2="430" y2="260" stroke-width="0.6"/>' +
        '<line x1="370" y1="300" x2="430" y2="300" stroke-width="0.6"/>' +
        '<polygon points="370,140 400,70 430,140" stroke-width="1.5" fill="none"/>' +
        '<line x1="400" y1="70" x2="400" y2="45" stroke-width="1"/>' +
        '<circle cx="400" cy="40" r="5" stroke-width="0.6"/>' +
        // Fenster Turm 2
        '<path d="M 390 160 Q 400 150 410 160 L 410 175 L 390 175 Z" stroke-width="0.5"/>' +
        '<path d="M 390 200 Q 400 190 410 200 L 410 215 L 390 215 Z" stroke-width="0.5"/>' +
        '<path d="M 390 240 Q 400 230 410 240 L 410 255 L 390 255 Z" stroke-width="0.5"/>' +
        '<rect x="390" y="280" width="20" height="15" stroke-width="0.5"/>' +
        // Turm 3 - rechts
        '<rect x="560" y="160" width="45" height="170" stroke-width="1.2"/>' +
        '<line x1="560" y1="200" x2="605" y2="200" stroke-width="0.5"/>' +
        '<line x1="560" y1="240" x2="605" y2="240" stroke-width="0.5"/>' +
        '<line x1="560" y1="280" x2="605" y2="280" stroke-width="0.5"/>' +
        '<polygon points="560,160 582,100 605,160" stroke-width="1.2" fill="none"/>' +
        '<line x1="582" y1="100" x2="582" y2="80" stroke-width="0.8"/>' +
        // Fenster Turm 3
        '<rect x="575" y="180" width="15" height="12" stroke-width="0.5"/>' +
        '<rect x="575" y="220" width="15" height="12" stroke-width="0.5"/>' +
        '<rect x="575" y="260" width="15" height="12" stroke-width="0.5"/>' +
        // Kirche/Kapelle links
        '<rect x="50" y="280" width="40" height="60" stroke-width="0.8"/>' +
        '<polygon points="50,280 70,250 90,280" stroke-width="0.8" fill="none"/>' +
        '<line x1="70" y1="250" x2="70" y2="235" stroke-width="0.6"/>' +
        '<path d="M 65 235 L 70 225 L 75 235" stroke-width="0.5"/>' +
        // Gebäude rechts
        '<rect x="700" y="270" width="50" height="60" stroke-width="0.8"/>' +
        '<path d="M 700 270 L 725 240 L 750 270" stroke-width="0.8"/>' +
        '<rect x="710" y="290" width="12" height="15" stroke-width="0.4"/>' +
        '<rect x="728" y="290" width="12" height="15" stroke-width="0.4"/>' +
        // Basis/Horizont
        '<line x1="0" y1="340" x2="170" y2="340" stroke-width="1"/>' +
        '<line x1="220" y1="340" x2="370" y2="340" stroke-width="1"/>' +
        '<line x1="430" y1="340" x2="560" y2="340" stroke-width="1"/>' +
        '<line x1="605" y1="330" x2="800" y2="330" stroke-width="1"/>' +
        '</svg>'
};