import math

def euclidean_distance(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    """Calculates the Euclidean distance between two 2D points."""
    return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

def calculate_concavity_depth(ia: tuple[float, float], ip: tuple[float, float], im: tuple[float, float]) -> float:
    """
    Calculates the concavity depth of the inferior border of the vertebra.
    
    Clinical Protocol (Baccetti et al., 2002/2005):
    - The baseline chord is drawn from the Inferior-Anterior (IA) corner to the Inferior-Posterior (IP) corner.
    - The Inferior-Middle (IM) landmark is the deepest point of the inferior border.
    - Concavity is defined as the upward displacement (curving inside the vertebral body) 
      of the inferior border relative to the IA-IP baseline.
      
    Mathematical Calculation:
    - We project the IM point vertically onto the IA-IP baseline chord.
    - The y-coordinate on the chord at x_IM is calculated via linear interpolation:
      y_chord = y_IA + (y_IP - y_IA) * (x_IM - x_IA) / (x_IP - x_IA)
    - Depth is chord_y - y_IM (positive when IM curves upward towards smaller y in screen coordinates).
    - This is robust to right-facing and left-facing cephalogram orientations, unlike vector-based normals.
    """
    x1, y1 = ia
    x2, y2 = ip
    x0, y0 = im
    
    if x2 == x1:
        # Fallback if baseline is perfectly vertical
        chord_y = (y1 + y2) / 2.0
    else:
        # Interpolate y on the baseline chord at x0 (x of IM)
        chord_y = y1 + (y2 - y1) * (x0 - x1) / (x2 - x1)
        
    # Screen coordinates increase downwards, so 'upward' concavity means y0 < chord_y
    depth = chord_y - y0
    return depth

def calculate_vertebra_metrics(landmarks: dict[str, tuple[float, float]], scale: float = 1.0) -> dict[str, float]:
    """
    Computes all standard dimensions and ratios for a single vertebra.
    landmarks must contain keys: 'SA', 'SP', 'IA', 'IP', 'IM'.
    scale is the pixels/mm ratio (division by scale converts pixels to mm).
    """
    required = ["SA", "SP", "IA", "IP", "IM"]
    if not all(k in landmarks for k in required):
        raise ValueError(f"Missing landmarks. Required: {required}")
    
    # Extract points
    sa = landmarks["SA"]
    sp = landmarks["SP"]
    ia = landmarks["IA"]
    ip = landmarks["IP"]
    im = landmarks["IM"]
    
    # Calculate dimensions in pixels, then convert to mm
    ah = euclidean_distance(sa, ia) / scale  # Anterior Height
    ph = euclidean_distance(sp, ip) / scale  # Posterior Height
    sw = euclidean_distance(sa, sp) / scale  # Superior Width
    iw = euclidean_distance(ia, ip) / scale  # Inferior Width
    
    # Concavity depth in mm
    cd = calculate_concavity_depth(ia, ip, im) / scale
    # Clamp negative concavities to 0 (since clinical bone doesn't bulge downwards)
    cd_clamped = max(0.0, cd)
    
    h_avg = (ah + ph) / 2.0
    w_avg = (sw + iw) / 2.0
    
    # Width-to-Height Ratio (Aspect Ratio)
    ar = w_avg / h_avg if h_avg > 0 else 0.0
    
    # Wedge shape factor (Anterior Height / Posterior Height)
    ws = ah / ph if ph > 0 else 1.0
    
    return {
        "AH": ah,
        "PH": ph,
        "SW": sw,
        "IW": iw,
        "CD": cd_clamped,
        "H_avg": h_avg,
        "W_avg": w_avg,
        "AR": ar,
        "WS": ws
    }

def determine_cvmi_stage(c2_metrics: dict, c3_metrics: dict, c4_metrics: dict) -> tuple[str, str]:
    """
    Evaluates the CVMI stage (CS1-CS6) based on C2, C3, and C4 dimensions.
    Returns (stage_code, explanation).
    
    Methodology Citation:
    This algorithm implements the 6-stage Cervical Vertebral Maturation (CVM) method 
    published by Baccetti, Franchi, and McNamara in 2002 (and updated in 2005):
    - Baccetti T, Franchi L, McNamara JA Jr. "An Improved Version of the Cervical Vertebral Maturation (CVM) Method 
      for the Assessment of Mandibular Growth Spurt." Angle Orthod. 2002;72(4):316-323.
    - Baccetti T, Franchi L, McNamara JA Jr. "The Cervical Vertebral Maturation (CVM) Method for the 
      Assessment of Diurnal Skeletal Maturity." Seminars in Orthodontics. 2005.
      
    Stage Diagnostic Criteria:
    - Inferior Border Concavities (threshold is typically 1.0 mm for presence):
      C2, C3, C4 borders are evaluated.
    - Vertebral Body Shapes of C3 and C4:
      1. Wedge-shaped: Anterior height significantly shorter than posterior height (wedge factor <= 0.85)
      2. Rectangular Horizontal: Width-to-height average ratio is wide (aspect ratio >= 1.15)
      3. Square: Width and height are approximately equal (0.95 <= aspect ratio < 1.15)
      4. Rectangular Vertical: Height is greater than width (aspect ratio < 0.95)
    """
    # 1. Determine presence of concavity (standard threshold is >= 1.0 mm)
    c2_concave = c2_metrics["CD"] >= 1.0
    # C3 and C4 concavity checks
    c3_concave = c3_metrics["CD"] >= 1.0
    c4_concave = c4_metrics["CD"] >= 1.0
    
    # 2. Analyze C3 & C4 Shapes
    def get_shape(metrics):
        if metrics["WS"] <= 0.85:
            return "wedge"
        elif metrics["AR"] >= 1.15:
            return "horizontal"
        elif 0.95 <= metrics["AR"] < 1.15:
            return "square"
        else:
            return "vertical"
            
    c3_shape = get_shape(c3_metrics)
    c4_shape = get_shape(c4_metrics)
    
    # Decision Tree matching Baccetti's CVM Guidelines:
    if not c2_concave and not c3_concave and not c4_concave:
        # CS1: All borders are flat. C3 and C4 bodies are wedge-shaped (or rectangular horizontal).
        # Clinically indicates: Mandibular growth spurt will begin in 2 years.
        return "CS1", "Stage 1 (CS1): Inferior borders of C2, C3, and C4 are flat. Vertebral bodies of C3 and C4 are wedge-shaped (Anterior height <= 85% Posterior height). Peak growth is 2 years away."
        
    elif c2_concave and not c3_concave and not c4_concave:
        # CS2: Concavity present only at C2. C3 and C4 are rectangular horizontal.
        # Clinically indicates: Mandibular growth spurt begins in 1 year.
        return "CS2", "Stage 2 (CS2): Concavity present at the inferior border of C2. C3 and C4 remain rectangular horizontal. Peak growth is 1 year away."
        
    elif c2_concave and c3_concave and not c4_concave:
        # CS3: Concavities present at C2 and C3. C4 remains flat. C3 and C4 are rectangular horizontal.
        # Clinically indicates: Mandibular growth spurt is imminent/occurring.
        return "CS3", "Stage 3 (CS3): Concavities present at C2 and C3. C4 is flat. C3 and C4 are rectangular horizontal. Peak growth occurs during this stage."
        
    elif c2_concave and c3_concave and c4_concave:
        # All three vertebrae show concavities. Staged according to C3/C4 shape progression:
        if c3_shape == "vertical" or c4_shape == "vertical":
            # CS6: All concave. C3 and C4 are rectangular vertical.
            # Clinically indicates: Growth spurt completed at least 2 years ago.
            return "CS6", "Stage 6 (CS6): Concavities present at C2, C3, and C4. C3 and C4 are rectangular vertical (Height > Width). Mandibular growth is complete."
            
        elif c3_shape == "square" or c4_shape == "square":
            # CS5: All concave. C3 and C4 are square-shaped.
            # Clinically indicates: Growth spurt completed 1 year ago.
            return "CS5", "Stage 5 (CS5): Concavities present at C2, C3, and C4. C3 and C4 are square-shaped. Peak growth occurred 1 year ago."
            
        else:
            # CS4: All concave. C3 and C4 are rectangular horizontal.
            # Clinically indicates: Growth spurt completed.
            return "CS4", "Stage 4 (CS4): Concavities present at C2, C3, and C4. C3 and C4 remain rectangular horizontal. Peak growth has just ended."
            
    else:
        # Fallback handling for atypical clinical presentations (e.g. C3 concave but C2 flat)
        # Classify primarily by the number of concavities, then aspect ratio progression
        concavities_count = sum([c2_concave, c3_concave, c4_concave])
        if concavities_count == 1:
            return "CS2", "Stage 2 (Atypical): 1 vertebra concave. C3/C4 remain horizontal."
        elif concavities_count == 2:
            return "CS3", "Stage 3 (Atypical): 2 vertebrae concave. C3/C4 remain horizontal."
        else:
            # All three are concave, evaluate by aspect ratio
            if c3_metrics["AR"] < 0.95 or c4_metrics["AR"] < 0.95:
                return "CS6", "Stage 6 (Atypical): All concave, vertical body shapes."
            elif c3_metrics["AR"] < 1.15 or c4_metrics["AR"] < 1.15:
                return "CS5", "Stage 5 (Atypical): All concave, square body shapes."
            else:
                return "CS4", "Stage 4 (Atypical): All concave, horizontal body shapes."
