// Marrakech - Koutoubia Mosque (Blueprint Style)
venues.marrakech = {
    name: 'KOUTOUBIA MOSQUE • MARRAKECH',
    taglineWPC: 'WPC Masters Marrakech',
    taglinePCL: 'PCL Masters Marrakech',
    badge: 'Marrakech',
    svg: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 400" fill="none" stroke="white" stroke-linecap="round" stroke-linejoin="round">' +
        // Minarett - Hauptturm
        '<rect x="340" y="60" width="120" height="260" stroke-width="1.5"/>' +
        '<line x1="340" y1="100" x2="460" y2="100" stroke-width="0.6"/>' +
        '<line x1="340" y1="140" x2="460" y2="140" stroke-width="0.6"/>' +
        '<line x1="340" y1="180" x2="460" y2="180" stroke-width="0.6"/>' +
        '<line x1="340" y1="220" x2="460" y2="220" stroke-width="0.6"/>' +
        '<line x1="340" y1="260" x2="460" y2="260" stroke-width="0.6"/>' +
        // Minarett Spitze
        '<rect x="360" y="35" width="80" height="25" stroke-width="1.2"/>' +
        '<rect x="375" y="15" width="50" height="20" stroke-width="1"/>' +
        '<polygon points="375,15 400,0 425,15" stroke-width="0.8" fill="none"/>' +
        '<line x1="400" y1="0" x2="400" y2="-15" stroke-width="0.8"/>' +
        '<circle cx="400" cy="-20" r="5" stroke-width="0.6"/>' +
        // Ornament-Bögen auf Minarett
        '<path d="M 355 75 Q 400 55 445 75" stroke-width="0.8"/>' +
        '<path d="M 355 115 Q 400 95 445 115" stroke-width="0.8"/>' +
        '<path d="M 355 155 Q 400 135 445 155" stroke-width="0.8"/>' +
        '<path d="M 355 195 Q 400 175 445 195" stroke-width="0.8"/>' +
        // Fenster im Minarett
        '<rect x="380" y="230" width="40" height="25" stroke-width="0.5"/>' +
        '<line x1="400" y1="230" x2="400" y2="255" stroke-width="0.4"/>' +
        '<rect x="380" y="270" width="40" height="25" stroke-width="0.5"/>' +
        '<line x1="400" y1="270" x2="400" y2="295" stroke-width="0.4"/>' +
        // Moschee-Gebäude links
        '<rect x="120" y="240" width="220" height="80" stroke-width="1.2"/>' +
        '<line x1="120" y1="270" x2="340" y2="270" stroke-width="0.5"/>' +
        '<line x1="120" y1="290" x2="340" y2="290" stroke-width="0.5"/>' +
        // Maurische Bögen links
        '<path d="M 140 260 Q 165 235 190 260 L 190 320 L 140 320 Z" stroke-width="0.8"/>' +
        '<path d="M 210 260 Q 235 235 260 260 L 260 320 L 210 320 Z" stroke-width="0.8"/>' +
        '<path d="M 280 260 Q 305 235 330 260 L 330 320 L 280 320 Z" stroke-width="0.8"/>' +
        // Moschee-Gebäude rechts
        '<rect x="460" y="240" width="220" height="80" stroke-width="1.2"/>' +
        '<line x1="460" y1="270" x2="680" y2="270" stroke-width="0.5"/>' +
        '<line x1="460" y1="290" x2="680" y2="290" stroke-width="0.5"/>' +
        // Maurische Bögen rechts
        '<path d="M 470 260 Q 495 235 520 260 L 520 320 L 470 320 Z" stroke-width="0.8"/>' +
        '<path d="M 540 260 Q 565 235 590 260 L 590 320 L 540 320 Z" stroke-width="0.8"/>' +
        '<path d="M 610 260 Q 635 235 660 260 L 660 320 L 610 320 Z" stroke-width="0.8"/>' +
        // Dachkuppeln auf Moschee
        '<path d="M 160 240 Q 190 210 220 240" stroke-width="0.8"/>' +
        '<path d="M 260 240 Q 290 210 320 240" stroke-width="0.8"/>' +
        '<path d="M 480 240 Q 510 210 540 240" stroke-width="0.8"/>' +
        '<path d="M 580 240 Q 610 210 640 240" stroke-width="0.8"/>' +
        // Seitliche Mauern/Anbauten
        '<path d="M 60 320 L 60 280 L 120 280 L 120 320" stroke-width="0.8"/>' +
        '<path d="M 680 320 L 680 280 L 740 280 L 740 320" stroke-width="0.8"/>' +
        // Palmen links
        '<line x1="80" y1="320" x2="80" y2="260" stroke-width="0.6"/>' +
        '<path d="M 80 260 Q 60 250 55 240" stroke-width="0.5"/>' +
        '<path d="M 80 260 Q 70 245 65 235" stroke-width="0.5"/>' +
        '<path d="M 80 260 Q 90 245 95 235" stroke-width="0.5"/>' +
        '<path d="M 80 260 Q 100 250 105 240" stroke-width="0.5"/>' +
        // Palmen rechts
        '<line x1="720" y1="320" x2="720" y2="260" stroke-width="0.6"/>' +
        '<path d="M 720 260 Q 700 250 695 240" stroke-width="0.5"/>' +
        '<path d="M 720 260 Q 710 245 705 235" stroke-width="0.5"/>' +
        '<path d="M 720 260 Q 730 245 735 235" stroke-width="0.5"/>' +
        '<path d="M 720 260 Q 740 250 745 240" stroke-width="0.5"/>' +
        // Basis/Boden
        '<line x1="30" y1="320" x2="770" y2="320" stroke-width="1"/>' +
        '<line x1="50" y1="335" x2="750" y2="335" stroke-width="0.5" opacity="0.6"/>' +
        // Pflasterung angedeutet
        '<line x1="200" y1="320" x2="200" y2="335" stroke-width="0.3" opacity="0.5"/>' +
        '<line x1="300" y1="320" x2="300" y2="335" stroke-width="0.3" opacity="0.5"/>' +
        '<line x1="400" y1="320" x2="400" y2="335" stroke-width="0.3" opacity="0.5"/>' +
        '<line x1="500" y1="320" x2="500" y2="335" stroke-width="0.3" opacity="0.5"/>' +
        '<line x1="600" y1="320" x2="600" y2="335" stroke-width="0.3" opacity="0.5"/>' +
        '</svg>'
};