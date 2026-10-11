"""Original vector ornament, category-specific compositions, no embedded credentials."""

import math

THEMES = {
    "general": ("#FBF8EF", "#142E43", "#B69B61", "#194462"),
    "affiliate": ("#F9F6EB", "#142E43", "#BA9D64", "#087C80"),
    "advanced": ("#102B42", "#F6F1E4", "#D4BE86", "#7297A7"),
    "accredited": ("#FBF0D2", "#173045", "#B28837", "#153348"),
    "president": ("#071521", "#FAF1D8", "#D6B26A", "#A88844"),
    "vice_president": ("#F7F5EC", "#173045", "#AA8C50", "#193D5B"),
    "founder": ("#073D33", "#FAF4DE", "#D8BD7A", "#7AAE96"),
    "honorary": ("#FCF7E7", "#173045", "#B49B60", "#7D683A"),
}


def _feather(x, y, scale=1, color="#B79A58", opacity=1):
    """Leaf/wing linework echoes the original emblem, without substituting its logo."""
    ribs = "".join(
        f'<path d="M0 {i*6} Q{-40+i*2} {i*6-10} -{46-i*2} {i*6-35}"/>'
        f'<path d="M0 {i*6} Q{40-i*2} {i*6-10} {46-i*2} {i*6-35}"/>'
        for i in range(1, 12)
    )
    return (
        f'<g transform="translate({x} {y}) scale({scale})" opacity="{opacity}" '
        f'fill="none" stroke="{color}" stroke-width="1.2">'
        '<path d="M0 85 Q-8 30 0 -25 Q8 30 0 85"/>' + ribs + '</g>'
    )


def _flourish(x, y, sx=1, sy=1, scale=1):
    """Engraved acanthus corner: closed leaves, veins and a paired scroll spine."""
    leaves = []
    for px, py, rotation, length in [(7,84,-12,1),(13,64,9,.95),(25,45,30,1),
                                     (44,25,56,1),(65,13,78,.95),(84,7,102,1)]:
        leaves.append(
            f'<g transform="translate({px} {py}) rotate({rotation}) scale({length})">'
            '<path d="M0 0 C-8 -5 -24 -2 -30 -17 C-18 -16 -10 -21 -3 -13 C1 -9 -2 -3 0 0Z" fill="url(#foil)" stroke="#A18142" stroke-width=".45"/>'
            '<path d="M0 0 Q-10 -12 -27 -16 M-9 -9 Q-10 -5 -18 -6" fill="none" stroke="#FCEDC4" stroke-width=".65"/>'
            '</g>'
        )
    return (
        f'<g transform="translate({x} {y}) scale({sx*scale} {sy*scale})">'
        '<path d="M0 110 C0 27 27 0 110 0" fill="none" stroke="url(#foil)" stroke-width="3"/>'
        '<path d="M6 108 C6 31 31 6 108 6" fill="none" stroke="#F1DDA7" stroke-width=".8"/>'
        '<path d="M3 109 C24 99 26 83 16 82 C7 81 8 94 17 92 M109 3 C99 24 83 26 82 16 C81 7 94 8 92 17" fill="none" stroke="url(#foil)" stroke-width="2.2"/>'
        + ''.join(leaves)
        + '<path d="M17 51 C17 22 40 12 51 17 C65 25 48 43 36 32 C28 24 36 20 42 25 M51 17 C22 17 12 40 17 51 C25 65 43 48 32 36 C24 28 20 36 25 42" fill="none" stroke="url(#foil)" stroke-width="1.3"/>'
        '</g>'
    )


def _texture(w, h, color):
    # Very fine quiet paper guilloche, never a seal or security claim.
    curves = ''.join(f'<path d="M-50 {i*18} Q{w*.22} {i*18-60} {w*.5} {i*18} T{w+50} {i*18}"/>' for i in range(int(h/18)+8))
    return f'<g fill="none" stroke="{color}" stroke-width=".3" opacity=".055">{curves}</g>'


def _guilloche(w, h, color, certificate=False):
    """Fine closed perimeter waves, with all document text zones kept clear."""
    top = 7 if not certificate else 11
    curves = []
    for i in range(30 if certificate else 22):
        offset = i * (0.35 if certificate else 0.25)
        coords = []
        for k in range(81):
            x = k*w/80
            y = top+offset+1.1*math.sin(k*math.pi/5+i*.35)
            coords.append(f'{x:.3f},{y:.3f}')
        points = ' '.join(coords)
        curves.append(f'<polyline points="{points}"/>')
        curves.append(f'<polyline points="{points}" transform="translate(0 {h}) scale(1 -1)"/>')
    return f'<g fill="none" stroke="{color}" stroke-width=".11" opacity=".55">'+''.join(curves)+'</g>'


def card_background(category, back=False):
    bg, fg, gold, accent = THEMES[category]
    defs = f'<defs><linearGradient id="foil" x2="1" y2="1"><stop stop-color="{gold}"/><stop offset=".35" stop-color="#F4DFAC"/><stop offset=".65" stop-color="{gold}"/><stop offset="1" stop-color="#8D6B30"/></linearGradient></defs>'
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 856 539.8">{defs}<rect width="856" height="539.8" fill="{bg}"/>']
    # Different border structures and perimeter silhouettes, not palette-only variants.
    if category == "general":
        parts += [f'<path d="M0 0 H122 Q10 24 0 160Z M856 539.8 H744 Q846 518 856 380Z" fill="{accent}"/>',
                  '<path d="M24 130 Q26 25 130 24 H758 Q831 26 832 95 V410 Q830 515 726 516 H98 Q25 514 24 445Z" fill="none" stroke="url(#foil)" stroke-width="2.3"/>']
        corners = [(28,28,1,1),(828,512,-1,-1)]
    elif category == "affiliate":
        parts += [f'<path d="M0 0 H115 Q-18 84 34 275 Q-20 472 115 539.8 H0Z M856 0 H813 Q859 100 825 244 Q861 400 813 539.8 H856Z" fill="{accent}"/>',
                  '<path d="M108 11 Q7 70 40 266 Q4 478 108 529 M811 11 Q845 130 820 263 Q846 412 811 529" fill="none" stroke="url(#foil)" stroke-width="3"/>']
        corners = [(12,14,1,1),(844,526,-1,-1)]
    elif category == "advanced":
        parts += ['<path d="M8 88 L88 8 H768 L848 88 V452 L768 531 H88 L8 452Z" fill="none" stroke="url(#foil)" stroke-width="3"/>',
                  f'<path d="M15 91 L91 15 H765 L841 91 V449 L765 525 H91 L15 449Z" fill="none" stroke="{accent}" stroke-width="1"/>']
        corners = [(28,28,1,1),(828,28,-1,1),(28,512,1,-1),(828,512,-1,-1)]
    elif category == "accredited":
        parts += [f'<path d="M0 0 H165 Q18 32 0 161Z M856 0 H756 Q842 35 856 111Z M856 539.8 H691 Q838 508 856 379Z M0 539.8 H100 Q15 504 0 429Z" fill="{accent}"/>',
                  '<rect x="15" y="15" width="826" height="509.8" rx="32" fill="none" stroke="url(#foil)" stroke-width="3.5"/>',
                  '<rect x="23" y="23" width="810" height="493.8" rx="27" fill="none" stroke="url(#foil)" stroke-width="1"/>']
        corners = [(22,22,1,1),(834,22,-1,1),(22,518,1,-1),(834,518,-1,-1)]
    elif category == "president":
        parts += ['<rect x="12" y="12" width="832" height="515.8" rx="23" fill="none" stroke="url(#foil)" stroke-width="3"/>',
                  '<rect x="22" y="22" width="812" height="495.8" rx="18" fill="none" stroke="url(#foil)" stroke-width=".8"/>',
                  '<path d="M30 440 Q8 265 30 80 M826 100 Q850 278 826 460" fill="none" stroke="url(#foil)" stroke-width="6"/>']
        corners = [(28,28,1,1),(828,28,-1,1),(28,512,1,-1),(828,512,-1,-1)]
    elif category == "vice_president":
        parts += [f'<path d="M0 0 H856 V27 H160 Q62 17 0 101Z M0 539.8 H856 V514 H696 Q794 524 856 439Z" fill="{accent}"/>',
                  '<path d="M12 103 Q47 14 165 14 H826 V437 Q791 526 673 526 H30Z" fill="none" stroke="url(#foil)" stroke-width="2.5"/>']
        corners = [(28,26,1,1),(828,514,-1,-1)]
    elif category == "founder":
        parts += ['<rect x="13" y="13" width="830" height="513.8" rx="34" fill="none" stroke="url(#foil)" stroke-width="2.8"/>',
                  '<path d="M29 142 Q8 273 29 402 M827 142 Q848 273 827 402" fill="none" stroke="url(#foil)" stroke-width="3"/>',
                  _feather(56,242,.6,gold,.8),_feather(800,242,.6,gold,.8)]
        corners = [(28,28,1,1),(828,28,-1,1),(28,512,1,-1),(828,512,-1,-1)]
    else:  # Honorary: double diplomatic frame, flourished mid-side medallions.
        parts += ['<rect x="15" y="15" width="826" height="509.8" rx="12" fill="none" stroke="url(#foil)" stroke-width="2.5"/>',
                  '<rect x="24" y="24" width="808" height="491.8" rx="9" fill="none" stroke="url(#foil)" stroke-width=".7"/>',
                  _feather(41,232,.42,gold,.7),_feather(815,232,.42,gold,.7)]
        corners = [(30,30,1,1),(826,30,-1,1),(30,510,1,-1),(826,510,-1,-1)]
    # Guilloche confined to perimeter bands. No flat ribbon crosses name/dates.
    parts += [_guilloche(856,539.8,gold),_texture(856,539.8,gold)]
    parts += [_flourish(x,y,sx,sy,.7 if category in {'general','affiliate'} else .85) for x,y,sx,sy in corners]
    if back:
        parts += [f'<path d="M324 180 V419" stroke="{gold}" stroke-width=".7" opacity=".55"/>', _feather(718,190,1.9,gold,.035)]
    parts += ['</svg>']
    return ''.join(parts).encode()


def certificate_background(participation=False):
    accent = '#15584B' if participation else '#142E43'
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1188 840"><defs><linearGradient id="foil" x2="1" y2="1"><stop stop-color="#977334"/><stop offset=".32" stop-color="#F1D89E"/><stop offset=".65" stop-color="#B6944E"/><stop offset="1" stop-color="#E4C58B"/></linearGradient></defs><rect width="1188" height="840" fill="#FBF8EF"/>',
             f'<rect x="21" y="21" width="1146" height="798" rx="6" fill="none" stroke="{accent}" stroke-width="22"/>',
             '<rect x="9" y="9" width="1170" height="822" rx="8" fill="none" stroke="url(#foil)" stroke-width="3"/>',
             '<rect x="35" y="35" width="1118" height="770" rx="8" fill="none" stroke="url(#foil)" stroke-width="3"/>',
             '<rect x="44" y="44" width="1100" height="752" rx="5" fill="none" stroke="url(#foil)" stroke-width=".8"/>',
             _guilloche(1188,840,'#DBBE7D',True),
             _texture(1188,840,'#AC8A47')]
    for x,y,sx,sy in [(38,38,1,1),(1150,38,-1,1),(38,802,1,-1),(1150,802,-1,-1)]:
        parts.append(_flourish(x,y,sx,sy,1.05))
        
    parts += ['<path d="M527 38 Q570 66 594 43 Q618 66 661 38 M527 802 Q570 774 594 797 Q618 774 661 802" fill="none" stroke="url(#foil)" stroke-width="2"/>','</svg>']
    return ''.join(parts).encode()
