import wx
import math
import numpy as np
from scipy import ndimage
from kipy.board_types import Via, BoardItem
from kipy.geometry import Vector2, Box2

class ViaStitcher:
    def __init__(self, board):
        self.board = board

    def rasterize_polygon(self, bitmap, nodes, bbox, resolution, value=1):
        """
        Rasterize a polygon onto a bitmap using scanline fill.
        
        Args:
            bitmap: 2D numpy array
            nodes: List of PolyLineNode objects
            bbox: Bounding box for coordinate transformation
            resolution: nm per pixel
            value: Value to add to pixels inside polygon
        """
        if len(nodes) < 3:
            return
            
        # Convert nodes to pixel coordinates
        points = []
        for node in nodes:
            px = int((node.point.x - bbox.pos.x) / resolution)
            py = int((node.point.y - bbox.pos.y) / resolution)
            points.append((px, py))
        
        # Scanline fill algorithm
        height, width = bitmap.shape
        
        for y in range(height):
            intersections = []
            for i in range(len(points)):
                p1 = points[i]
                p2 = points[(i + 1) % len(points)]
                
                if p1[1] == p2[1]:  # Horizontal edge
                    continue
                    
                if y < min(p1[1], p2[1]) or y >= max(p1[1], p2[1]):
                    continue
                
                # Calculate x intersection
                x = p1[0] + (y - p1[1]) * (p2[0] - p1[0]) / (p2[1] - p1[1])
                intersections.append(int(x))
            
            intersections.sort()
            
            # Fill between pairs of intersections
            for i in range(0, len(intersections) - 1, 2):
                x1 = max(0, intersections[i])
                x2 = min(width - 1, intersections[i + 1])
                if x1 <= x2:
                    bitmap[y, x1:x2+1] += value

    def rasterize_zones_by_layer(self, zones, bbox, resolution):
        """
        Create a bitmap where each pixel value = number of layers with zone coverage.
        
        Returns:
            2D numpy array with layer counts
        """
        width = int(bbox.size.x / resolution) + 1
        height = int(bbox.size.y / resolution) + 1
        bitmap = np.zeros((height, width), dtype=np.int32)
        
        # Track which layers we've seen at each pixel
        layer_maps = {}
        
        for zone in zones:
            if not hasattr(zone, 'filled_polygons'):
                continue
                
            polys_dict = zone.filled_polygons
            if not hasattr(polys_dict, 'values'):
                continue
            
            for layer_id, poly_list in polys_dict.items():
                if not poly_list:
                    continue
                    
                # Create layer-specific bitmap if needed
                if layer_id not in layer_maps:
                    layer_maps[layer_id] = np.zeros((height, width), dtype=np.uint8)
                
                for poly in poly_list:
                    if not hasattr(poly, 'outline') or not hasattr(poly.outline, 'nodes'):
                        continue
                    
                    nodes = list(poly.outline.nodes)
                    self.rasterize_polygon(layer_maps[layer_id], nodes, bbox, resolution, value=1)
                    
                    # Handle holes
                    if hasattr(poly, 'holes'):
                        for hole in poly.holes:
                            if hasattr(hole, 'nodes'):
                                hole_nodes = list(hole.nodes)
                                # Subtract hole (set to 0)
                                temp = np.zeros((height, width), dtype=np.uint8)
                                self.rasterize_polygon(temp, hole_nodes, bbox, resolution, value=1)
                                layer_maps[layer_id] = np.where(temp > 0, 0, layer_maps[layer_id])
        
        # Count layers at each pixel
        for layer_bitmap in layer_maps.values():
            bitmap += (layer_bitmap > 0).astype(np.int32)
        
        return bitmap

    def rasterize_obstacles(self, net_name, bbox, resolution, ignored_zone_ids=None):
        """
        Create a bitmap of all obstacles (pads, tracks, vias, zones of other nets).
        
        Args:
            ignored_zone_ids: Set of zone UUIDs to skip.
            
        Returns:
            2D numpy array (1 = obstacle, 0 = free)
        """
        if ignored_zone_ids is None:
            ignored_zone_ids = set()
            
        width = int(bbox.size.x / resolution) + 1
        height = int(bbox.size.y / resolution) + 1
        bitmap = np.zeros((height, width), dtype=np.uint8)
        
        def to_pixel(pos):
            px = int((pos.x - bbox.pos.x) / resolution)
            py = int((pos.y - bbox.pos.y) / resolution)
            return px, py
        
        def draw_circle(cx, cy, radius_px):
            """Draw filled circle on bitmap"""
            y_coords, x_coords = np.ogrid[:height, :width]
            mask = (x_coords - cx)**2 + (y_coords - cy)**2 <= radius_px**2
            bitmap[mask] = 1
        
        def draw_line(x1, y1, x2, y2, width_px):
            """Draw thick line on bitmap"""
            # Bresenham with thickness
            dx = abs(x2 - x1)
            dy = abs(y2 - y1)
            sx = 1 if x1 < x2 else -1
            sy = 1 if y1 < y2 else -1
            err = dx - dy
            
            points = []
            while True:
                points.append((x1, y1))
                if x1 == x2 and y1 == y2:
                    break
                e2 = 2 * err
                if e2 > -dy:
                    err -= dy
                    x1 += sx
                if e2 < dx:
                    err += dx
                    y1 += sy
            
            # Draw circles at each point for thickness
            for px, py in points:
                draw_circle(px, py, width_px // 2)
        
        # Pads
        for p in self.board.get_pads():
            if p.net and p.net.name == net_name:
                continue
            
            px, py = to_pixel(p.position)
            
            # Get pad size
            radius_nm = 1000000  # Default 1mm
            if hasattr(p, 'padstack') and hasattr(p.padstack, 'copper_layers'):
                try:
                    for layer in p.padstack.copper_layers:
                        if hasattr(layer, 'size'):
                            curr_max = max(layer.size.x, layer.size.y)
                            if curr_max > radius_nm:
                                radius_nm = curr_max
                except:
                    pass
            
            radius_px = int(radius_nm / resolution / 2)
            draw_circle(px, py, radius_px)
        
        # Vias
        for v in self.board.get_vias():
            if v.net and v.net.name == net_name:
                continue
            px, py = to_pixel(v.position)
            radius_px = int(v.diameter / resolution / 2)
            draw_circle(px, py, radius_px)
        
        # Tracks
        for t in self.board.get_tracks():
            if t.net and t.net.name == net_name:
                continue
            x1, y1 = to_pixel(t.start)
            x2, y2 = to_pixel(t.end)
            width_px = int(t.width / resolution)
            draw_line(x1, y1, x2, y2, width_px)
        
        # Zones of other nets
        for zone in self.board.get_zones():
            if zone.net and zone.net.name == net_name:
                continue
            if not zone.filled:
                continue
                
            # Check if ignored
            if hasattr(zone.id, 'value'):
                z_id = zone.id.value
            else:
                z_id = str(zone.id)
                
            if z_id in ignored_zone_ids:
                continue
                
            if not hasattr(zone, 'filled_polygons'):
                continue
            
            polys_dict = zone.filled_polygons
            if not hasattr(polys_dict, 'values'):
                continue
            
            for poly_list in polys_dict.values():
                if not poly_list:
                    continue
                for poly in poly_list:
                    if not hasattr(poly, 'outline') or not hasattr(poly.outline, 'nodes'):
                        continue
                    nodes = list(poly.outline.nodes)
                    self.rasterize_polygon(bitmap, nodes, bbox, resolution, value=1)
        
        return bitmap

    def apply_clearance(self, bitmap, clearance_nm, resolution):
        """
        Apply clearance by eroding the valid area (or equivalently, dilating obstacles).
        
        Args:
            bitmap: Binary bitmap (1 = valid, 0 = invalid)
            clearance_nm: Clearance in nanometers
            resolution: nm per pixel
            
        Returns:
            Eroded bitmap
        """
        clearance_px = int(clearance_nm / resolution)
        if clearance_px < 1:
            return bitmap
        
        # Erosion = shrink valid areas
        structure = np.ones((2*clearance_px+1, 2*clearance_px+1))
        eroded = ndimage.binary_erosion(bitmap, structure=structure)
        return eroded.astype(np.uint8)

    def get_candidate_nets(self):
        """
        Finds nets that have filled zones on at least two different copper layers.
        Returns a sorted list of net names.
        """
        nets_with_zones = {}
        
        # Iterate over all zones to map nets to layers
        for zone in self.board.get_zones():
            if not zone.filled:
                continue
                
            net = zone.net
            if not net or net.name == "":
                continue
            
            # Assuming 'layers' is a list of existing layer IDs in the zone
            # or zone.layer is a single layer. API docs say 'layers' for Zone.
            # We want unique physical copper layers.
            # Convert layer IDs to check if they are copper? 
            # For now, just track the layer IDs.
            if net.name not in nets_with_zones:
                nets_with_zones[net.name] = set()
            
            # Zone.layers returns a list of layer IDs
            for layer_id in zone.layers:
                nets_with_zones[net.name].add(layer_id)

        # Filter for nets with > 1 layer
        candidates = []
        for net_name, layers in nets_with_zones.items():
            if len(layers) > 1:
                candidates.append(net_name)
        
        return sorted(candidates)

    def get_other_zones(self, target_net_name):
        """
        Returns a list of zones that belong to other nets.
        Format: [{'id': str, 'name': str, 'net': str, 'layers': list}]
        """
        other_zones = []
        for zone in self.board.get_zones():

            net_name = zone.net.name if zone.net else "No Net"
            if net_name == target_net_name:
                continue
                
            # Only include filled zones as obstacles
            if not zone.filled:
                continue
                
            # Get internal ID
            if hasattr(zone.id, 'value'):
                z_id = zone.id.value
            else:
                z_id = str(zone.id)
                
            layers = list(zone.layers)
            
            other_zones.append({
                'id': z_id,
                'net': net_name,
                'layers': layers
            })
            
        return other_zones




    def stitch(self, net_name, via_diameter, via_drill, grid_x, grid_y, stagger, ignored_zone_ids=None, refill_after=True, progress_callback=None):
        """
        Generates stitching vias.
        
        Args:
            net_name (str): Name of the net to stitch.
            via_diameter (float): Diameter of via in mm.
            via_drill (float): Drill size in mm.
            grid_x (float): X spacing in mm.
            grid_y (float): Y spacing in mm.
            stagger (bool): Whether to stagger rows.
            ignored_zone_ids (list): List of zone UUIDs to ignore.
            refill_after (bool): If True, refill all zones after stitching.
            progress_callback (callable): Optional callback(percent, status) for progress updates.
        
        Returns:
            int: Number of vias added.
        """
        if ignored_zone_ids is None:
            ignored_zone_ids = set()
        else:
            ignored_zone_ids = set(ignored_zone_ids)
            
        # 1. Get Net Object and Zones
        target_net = None
        # Nets can be retrieved by get_nets(). Need finding by name.
        # Ideally board.get_nets() returns a map or list.
        # We'll just iterate for now.
        for net in self.board.get_nets():
            if net.name == net_name:
                target_net = net
                break
        
        if not target_net:
            return 0

        # Get all zones for this net
        zones = [z for z in self.board.get_zones() if z.net and z.net.name == net_name and z.filled]
        
        if progress_callback:
            progress_callback(10, "Found zones for net")
        
        if not zones:
            return 0



        # 2. Determine Bounding Box for Stitching
        # We want the union of all bounding boxes of these zones.
        overall_bbox = None
        for z in zones:
            bb = z.bounding_box()
            if overall_bbox is None:
                overall_bbox = bb
            else:
                overall_bbox = overall_bbox.merge(bb) # Use merge based on API docs
        
        if overall_bbox is None:
            return 0
            
        # 2b. Generate Bitmaps
        # Resolution: 100000 nm = 0.1mm per pixel (good balance of accuracy vs performance)
        RESOLUTION = 100000
        CLEARANCE = 250000  # 0.25mm
        
        # Step 1: Rasterize target net zones (count layers)
        if progress_callback:
            progress_callback(15, "Rasterizing target zones...")
        zone_bitmap = self.rasterize_zones_by_layer(zones, overall_bbox, RESOLUTION)
        
        if progress_callback:
            progress_callback(35, "Rasterizing obstacles...")
        
        # Step 2: Rasterize all obstacles
        obstacle_bitmap = self.rasterize_obstacles(net_name, overall_bbox, RESOLUTION, ignored_zone_ids)
        
        if progress_callback:
            progress_callback(55, "Applying boolean operations...")
        
        # Step 3: Create valid area bitmap (zones with >=2 layers AND no obstacles)
        valid_bitmap = (zone_bitmap >= 2) & (obstacle_bitmap == 0)
        
        # Step 4: Apply clearance by eroding valid areas
        if progress_callback:
            progress_callback(60, "Applying clearance...")
        valid_bitmap = self.apply_clearance(valid_bitmap.astype(np.uint8), CLEARANCE, RESOLUTION)
        
        if progress_callback:
            progress_callback(65, "Generating via grid...")
            
        # Convert mm to internal units if necessary? 
        # API usually exposes coords in mm or internal units. 
        # Vector2 docs didn't specify, but usually KiCad Python bindings strive for mm or use unit conversions.
        # However, kipy docs have 'common_types' which might imply standard units.
        # Let's assume the coordinates from 'bounding_box()' are compatible with 'via.position'.
        # We will assume they are in the SAME system (likely nanometers or mm).
        # We need to test this.
        
        # 3. Generate Points
        start_x = overall_bbox.pos.x
        start_y = overall_bbox.pos.y
        end_x = start_x + overall_bbox.size.x
        end_y = start_y + overall_bbox.size.y
        
        # Assuming units are consistent. If units are mm, grid_x/y work directly.
        # If units are nm, we need conversion. 
        # Standard KiCad native units are integers (nm). 
        # kipy might wrap this. Let's assume kipy handles units transparently or exposes them.
        # From the `ipc_entry.py` sample, it uses `get_socket_path`, standard python stuff.
        # Let's try to assume mm for input params, but we might need to check BBox magnitude.
        # If BBox is huge (e.g. 100000000), it's nm. If it's 100, it's mm.
        # Safer: Input grid is user-facing (mm).
        
        # Let's assume for now we are working in the board's coordinate system.
        # We'll need a way to verify units. 
        # For now, let's treat grid_x, grid_y as deltas in the same unit system as bbox.
        # But wait, user inputs 5 (mm). If board is nm, we place 5nm apart!
        # Check `board.get_design_settings()`. 
        # Actually, let's look at `ui.py` later for unit handling or just use a safe conversion factor.
        # Standard KiCad 1 mm = 1,000,000 nm.
        # Let's guess: kipy returns `Vector2` which often wraps C++ `VECTOR2I` (nm).
        SCALE = 1000000 # 1mm in nm
        
        gx = int(grid_x * SCALE)
        gy = int(grid_y * SCALE)
        
        # Ensure we don't loop forever if grid is 0
        if gx <= 0: gx = int(1 * SCALE)
        if gy <= 0: gy = int(1 * SCALE)

        vias_to_add = []
        
        # Calculate total grid points for progress
        total_cols = int((end_x - start_x) / gx) + 1
        total_rows = int((end_y - start_y) / gy) + 1
        total_points = total_cols * total_rows
        points_checked = 0
        
        x = start_x
        row = 0
        while x <= end_x:
            y = start_y
            
            # Apply stagger
            offset_y = 0
            if stagger and (row % 2 == 1):
                offset_y = gy // 2
            
            y += offset_y
            
            while y <= end_y:
                pt = Vector2()
                pt.x = int(x)
                pt.y = int(y)
                
                # 4. Check Validity using bitmap
                # Convert position to pixel coordinates
                px = int((x - overall_bbox.pos.x) / RESOLUTION)
                py = int((y - overall_bbox.pos.y) / RESOLUTION)
                
                # Check bounds
                height, width = valid_bitmap.shape
                if 0 <= px < width and 0 <= py < height:
                    if valid_bitmap[py, px] > 0:
                        # Valid location!
                        v = Via() 
                        v.position = pt
                        v.net = target_net
                        v.diameter = int(via_diameter * SCALE)
                        v.drill_diameter = int(via_drill * SCALE)
                        
                        vias_to_add.append(v)
                
                y += gy
                points_checked += 1
                
            x += gx
            row += 1
            
            # Update progress during grid iteration (65-90%)
            if progress_callback and total_points > 0:
                grid_progress = 65 + (25 * points_checked / total_points)
                progress_callback(grid_progress, f"Checking grid points ({points_checked}/{total_points})...")
            
        # 5. Commit
        if progress_callback:
            progress_callback(90, f"Committing {len(vias_to_add)} vias...")
            
        if vias_to_add:
            try:
                # Group undo
                commit = self.board.begin_commit()
                self.board.create_items(vias_to_add)
                self.board.push_commit(commit)
                
                # Add all created vias to selection for easy grouping
                # User can then create a group from the selection in KiCad
                if progress_callback:
                    progress_callback(95, "Selecting created vias...")
                    
                self.board.clear_selection()
                for v in vias_to_add:
                    self.board.add_to_selection(v)
                    
            except Exception as e:
                print(f"Error adding vias: {e}")
        

        if refill_after:
            # Refill zones after stitching (only if refill_islands wasn't used)
            if progress_callback:
                progress_callback(99, "Refilling zones...")
            
            self.board.refill_zones()
                
        return len(vias_to_add)
