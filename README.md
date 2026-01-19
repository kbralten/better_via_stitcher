# **Better Via Stitcher for KiCad**

**Better Via Stitcher** is a powerful, automated via-stitching plugin for KiCad designed to simplify the process of thermal management and ground plane stitching. Unlike the standard "Add Stitching Vias" tool, this plugin provides advanced grid controls, intelligent net detection, and grouped manipulation.

## **Key Features**

* **Intelligent Net Selection:** Automatically filters for nets that have filled areas on multiple layers, while allowing manual selection of any board net.  
* **Dynamic Layer Sensing:** Automatically identifies overlapping filled areas (whether from the same zone on multiple layers or different overlapping zones) to determine valid stitching regions.  
* **Advanced Grid Layouts:** \- Configure precise X and Y spacing.  
  * **Staggered Grid Support:** Option to offset every other row by 1/2 the grid spacing for better thermal distribution and shielding.  
* **Integrated DRC Guardrails:** Vias are only placed where they won't cause DRC violations with other nets, board edges, or hole-to-hole clearance requirements.  
* **"Punch Through" Mode:** Option to "Ignore areas on other nets," allowing the stitcher to place vias even if they would cut through filled zones of different nets (while still respecting traces and pads).  

## **How to Use**

1. **Open the Plugin:** Click the "Better Via Stitcher" icon in the PCB Editor toolbar.  
2. **Select Net:** Choose the net you wish to stitch. The dropdown defaults to nets with existing copper pours on multiple layers.  
3. **Configure Vias:** Select the desired via size and drill.  
4. **Set Grid:** Enter your desired spacing. Check **Stagger Rows** if you want a triangular/hexagonal pattern.  
5. **Placement Rules:**  
   * Use "Ignore other zones" if you want the stitcher to be aggressive and disregard copper pours from other nets during DRC checks.  
6. **Run:** Click **Generate**. The vias will appear and be automatically grouped.

## **Roadmap & Planned Features**

* **Boundary Clearance:** Add an input to keep vias a configurable distance (in mm) away from the zone edges to improve manufacturability.  
* **Selection Constraint:** Add "Only stitch within selected area" functionality, allowing the user to constrain via generation to one or more Rule Areas or specific filled zones.  
* **Same-Net Pad Avoidance:** Implementation of safety logic to ensure vias do not land immediately adjacent to component pads on the same net, preventing soldering issues.  
* **Advanced Island Stitching:** A specialized multi-pass routine to rescue isolated copper islands:  
  1. Temporarily disable "Remove unconnected islands" in zone settings.  
  2. Refill the zone to identify all potential copper areas.  
  3. Perform standard grid-based stitching.  
  4. Detect remaining isolated islands and attempt to place at least one via using a high-density localized pattern.  
  5. Restore original island removal settings.