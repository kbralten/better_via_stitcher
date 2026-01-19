import wx
from stitcher import ViaStitcher

class ViaStitcherDialog(wx.Dialog):
    def __init__(self, parent, board, client):
        super().__init__(parent, title="Better Via Stitcher", size=(450, 600))
        
        self.board = board
        self.client = client
        self.stitcher = ViaStitcher(board)
        
        self.init_ui()
        
    def init_ui(self):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        # Header
        info_text = wx.StaticText(panel, label="Configure Stitching Parameters")
        font = info_text.GetFont()
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        info_text.SetFont(font)
        vbox.Add(info_text, 0, wx.ALL | wx.CENTER, 10)
        
        # Grid for form inputs
        grid_sizer = wx.FlexGridSizer(rows=8, cols=2, vgap=10, hgap=10)
        
        # 1. Net Selection
        grid_sizer.Add(wx.StaticText(panel, label="Net:"), 0, wx.ALIGN_CENTER_VERTICAL)
        candidates = self.stitcher.get_candidate_nets()
        if not candidates:
            candidates = ["No overlapping zones found"]
            
        self.net_choice = wx.Choice(panel, choices=candidates)
        self.net_choice.Bind(wx.EVT_CHOICE, self.on_net_change)
        
        if candidates and "GND" in candidates:
             self.net_choice.SetStringSelection("GND")
        elif candidates:
             self.net_choice.SetSelection(0)
             
        grid_sizer.Add(self.net_choice, 1, wx.EXPAND)
        
        # 2. Via Diameter
        grid_sizer.Add(wx.StaticText(panel, label="Via Diameter (mm):"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.via_dia = wx.TextCtrl(panel, value="0.6")
        grid_sizer.Add(self.via_dia, 1, wx.EXPAND)
        
        # 3. Via Drill
        grid_sizer.Add(wx.StaticText(panel, label="Via Drill (mm):"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.via_drill = wx.TextCtrl(panel, value="0.3")
        grid_sizer.Add(self.via_drill, 1, wx.EXPAND)
        
        # 4. Grid X
        grid_sizer.Add(wx.StaticText(panel, label="Grid X (mm):"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.grid_x = wx.TextCtrl(panel, value="2.5")
        grid_sizer.Add(self.grid_x, 1, wx.EXPAND)
        
        # 5. Grid Y
        grid_sizer.Add(wx.StaticText(panel, label="Grid Y (mm):"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.grid_y = wx.TextCtrl(panel, value="2.5")
        grid_sizer.Add(self.grid_y, 1, wx.EXPAND)

        # 6. Offset X
        grid_sizer.Add(wx.StaticText(panel, label="Offset X (mm):"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.offset_x = wx.TextCtrl(panel, value="0.0")
        grid_sizer.Add(self.offset_x, 1, wx.EXPAND)

        # 7. Offset Y
        grid_sizer.Add(wx.StaticText(panel, label="Offset Y (mm):"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.offset_y = wx.TextCtrl(panel, value="0.0")
        grid_sizer.Add(self.offset_y, 1, wx.EXPAND)



        # 6. Options
        grid_sizer.Add(wx.StaticText(panel, label="Options:"), 0, wx.ALIGN_CENTER_VERTICAL)
        options_sizer = wx.BoxSizer(wx.VERTICAL)
        self.chk_stagger = wx.CheckBox(panel, label="Stagger Rows")
        options_sizer.Add(self.chk_stagger, 0, wx.BOTTOM, 5)
        
        self.chk_refill_after = wx.CheckBox(panel, label="Refill Zones After Stitching")
        self.chk_refill_after.SetValue(True)  # Checked by default
        options_sizer.Add(self.chk_refill_after, 0, wx.BOTTOM, 5)
        grid_sizer.Add(options_sizer, 1, wx.EXPAND)
        
        vbox.Add(grid_sizer, 0, wx.ALL | wx.EXPAND, 15)
        
        # 7. Zone Ignore List
        vbox.Add(wx.StaticText(panel, label="Ignore Zones from Other Nets (Punch Through):"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 15)
        self.zone_list = wx.CheckListBox(panel, size=(-1, 120))
        self.zone_ids = [] # Store IDs corresponding to list items
        vbox.Add(self.zone_list, 1, wx.ALL | wx.EXPAND, 15)
        
        self.update_zone_list()
        
        # Progress section
        progress_box = wx.BoxSizer(wx.VERTICAL)
        
        self.status_label = wx.StaticText(panel, label="Ready")
        progress_box.Add(self.status_label, 0, wx.BOTTOM, 5)
        
        self.progress_bar = wx.Gauge(panel, range=100)
        progress_box.Add(self.progress_bar, 0, wx.EXPAND)
        
        vbox.Add(progress_box, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 15)
        
        # Buttons
        btnsizer = wx.StdDialogButtonSizer()
        
        self.ok_btn = wx.Button(panel, wx.ID_OK, label="Generate Vias")
        self.ok_btn.Bind(wx.EVT_BUTTON, self.on_stitch)
        btnsizer.AddButton(self.ok_btn)
        
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        btnsizer.AddButton(cancel_btn)
        btnsizer.Realize()
        
        vbox.Add(btnsizer, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        
        panel.SetSizer(vbox)
        
    def on_net_change(self, event):
        self.update_zone_list()
        

        
    def update_zone_list(self):
        """Update the checklist of other zones based on target net"""
        target_net = self.net_choice.GetStringSelection()
        other_zones = self.stitcher.get_other_zones(target_net)
        
        self.zone_list.Clear()
        self.zone_ids = []
        
        for z in other_zones:
            layers_str = ", ".join(str(l) for l in z['layers'])
            label = f"Net: {z['net']} (Layers: {layers_str})"
            self.zone_list.Append(label)
            self.zone_ids.append(z['id'])
            
    def update_progress(self, percent, status):
        """Update progress bar and status label"""
        self.progress_bar.SetValue(int(percent))
        self.status_label.SetLabel(status)
        wx.SafeYield()  # Allow UI to update
        
    def on_stitch(self, event):
        net_name = self.net_choice.GetStringSelection()
        
        try:
            dia = float(self.via_dia.GetValue())
            drill = float(self.via_drill.GetValue())
            gx = float(self.grid_x.GetValue())
            gy = float(self.grid_y.GetValue())
            off_x = float(self.offset_x.GetValue())
            off_y = float(self.offset_y.GetValue())
            stagger = self.chk_stagger.GetValue()
            refill_after = self.chk_refill_after.GetValue()
        except ValueError:
            wx.MessageBox("Invalid input values. Please check numbers.", "Error", wx.OK | wx.ICON_ERROR)
            return

        if gx <= 0 or gy <= 0:
            wx.MessageBox("Grid spacing must be positive.", "Error", wx.OK | wx.ICON_ERROR)
            return

        # Disable button to prevent double clicks
        self.ok_btn.Disable()
        self.progress_bar.SetValue(0)
        self.status_label.SetLabel("Starting...")
        
        # Collect ignored zones
        ignored_ids = []
        for i in range(self.zone_list.GetCount()):
            if self.zone_list.IsChecked(i):
                ignored_ids.append(self.zone_ids[i])
                
        try:
            count = self.stitcher.stitch(
                net_name, 
                via_diameter=dia, 
                via_drill=drill, 
                grid_x=gx, 
                grid_y=gy, 
                offset_x=off_x,
                offset_y=off_y,
                stagger=stagger, 
                ignored_zone_ids=ignored_ids,
                refill_after=refill_after,
                progress_callback=self.update_progress
            )
            
            self.progress_bar.SetValue(100)
            self.status_label.SetLabel(f"Complete - {count} vias placed")
            wx.MessageBox(f"Successfully placed {count} stitching vias.", "Result", wx.OK | wx.ICON_INFORMATION)
            self.EndModal(wx.ID_OK)
            
        except Exception as e:
            self.progress_bar.SetValue(0)
            self.status_label.SetLabel("Error occurred")
            wx.MessageBox(f"Error during stitching: {str(e)}", "Error", wx.OK | wx.ICON_ERROR)
            import traceback
            traceback.print_exc()
        finally:
             self.ok_btn.Enable()
