from PyQt6.QtWidgets import QStyledItemDelegate, QApplication, QStyle, QStyleOptionButton, QToolTip
from PyQt6.QtCore import Qt, QRect, QSize, pyqtSignal, QEvent
from PyQt6.QtGui import QMouseEvent, QHelpEvent, QColor, QIcon, QPainter

class ActionDelegate(QStyledItemDelegate):
    """
    Delegate to render buttons in the 'Actions' column.
    Buttons: [Open File] [Open Folder] [ToC Status]
    """
    
    # Emits row index and action type
    action_requested = pyqtSignal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.hover_row = -1
        self.hover_button = 0 # 0=None, 1=File, 2=Folder, 3=ToC
        
        # Cache icons
        self.icon_file = QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        self.icon_folder = QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        # For ToC, we'll use a book icon if available, or a generic one colored
        # SP_FileDialogDetailedView is list-like, maybe appropriate.
        self.icon_toc = QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogInfoView) 

    def paint(self, painter, option, index):
        if index.column() == 7: # Action Column
            rect = option.rect
            width = rect.width()
            height = rect.height()
            
            # Button layout: 3 buttons
            count = 3
            btn_width = width // count
            
            # Get Data
            user_data = index.data(Qt.ItemDataRole.UserRole)
            has_toc = user_data.get('has_toc', False) if user_data else False
            
            is_hovering_cell = (self.hover_row == index.row())

            # --- Button 1: Open File ---
            self._draw_btn(painter, rect, 0, btn_width, height, 
                           self.icon_file, "Open File", 1, is_hovering_cell)

            # --- Button 2: Open Folder ---
            self._draw_btn(painter, rect, 1, btn_width, height, 
                           self.icon_folder, "Open Folder", 2, is_hovering_cell)
            
            # --- Button 3: ToC Status ---
            # Custom color logic
            # Paint a colored background or colored icon frame
            toc_rect = QRect(rect.left() + (2 * btn_width), rect.top(), btn_width, height)
            toc_rect.adjust(2, 2, -2, -2)
            
            # Color indicator: Red (No ToC) / Green (Has ToC)
            color = QColor("#28a745") if has_toc else QColor("#dc3545") # Bootstrap Green/Red
            
            # Draw standard button frame first
            btn_opt = QStyleOptionButton()
            btn_opt.rect = toc_rect
            btn_opt.icon = self.icon_toc
            btn_opt.iconSize = QSize(16, 16)
            btn_opt.state = QStyle.StateFlag.State_Enabled | QStyle.StateFlag.State_Raised
            if is_hovering_cell and self.hover_button == 3:
                btn_opt.state |= QStyle.StateFlag.State_MouseOver | QStyle.StateFlag.State_Active
            
            QApplication.style().drawControl(QStyle.ControlElement.CE_PushButton, btn_opt, painter)
            
            # Overlay a colored indicator (small circle or stripe)
            painter.save()
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            # Draw small dot bottom-right
            dot_size = 6
            painter.drawEllipse(toc_rect.right() - dot_size - 2, toc_rect.bottom() - dot_size - 2, dot_size, dot_size)
            painter.restore()

        else:
            super().paint(painter, option, index)

    def _draw_btn(self, painter, cell_rect, index, w, h, icon, tooltip, btn_id, is_hovering_cell):
        rect = QRect(cell_rect.left() + (index * w), cell_rect.top(), w, h)
        rect.adjust(2, 2, -2, -2)
        
        opt = QStyleOptionButton()
        opt.rect = rect
        opt.icon = icon
        opt.iconSize = QSize(16, 16)
        opt.state = QStyle.StateFlag.State_Enabled | QStyle.StateFlag.State_Raised
        if is_hovering_cell and self.hover_button == btn_id:
            opt.state |= QStyle.StateFlag.State_MouseOver | QStyle.StateFlag.State_Active
        
        QApplication.style().drawControl(QStyle.ControlElement.CE_PushButton, opt, painter)

    def editorEvent(self, event, model, option, index):
        if index.column() == 7:
            rect = option.rect
            width = rect.width()
            btn_width = width // 3
            
            if event.type() == QEvent.Type.MouseMove:
                click_x = event.pos().x()
                local_x = click_x - rect.left()
                
                new_btn = 0
                if local_x < btn_width: new_btn = 1
                elif local_x < btn_width * 2: new_btn = 2
                else: new_btn = 3
                
                if (self.hover_row != index.row()) or (self.hover_button != new_btn):
                    self.hover_row = index.row()
                    self.hover_button = new_btn
                    
                    # Force repaint
                    view = self.parent()
                    if view: view.update(index)
                    # Clear prev row if changed (omitted for brevity, handled by Leave)
                return True
                
            elif event.type() == QEvent.Type.Leave:
                self.hover_row = -1
                self.hover_button = 0
                view = self.parent()
                if view: view.viewport().update() # Redraw all simpler
                return True

            elif event.type() == QEvent.Type.MouseButtonRelease:
                click_x = event.pos().x()
                local_x = click_x - rect.left()
                
                if local_x < btn_width:
                    self.action_requested.emit(index.row(), 'open_file')
                elif local_x < btn_width * 2:
                    self.action_requested.emit(index.row(), 'open_folder')
                else:
                    self.action_requested.emit(index.row(), 'toc_action')
                return True

        return super().editorEvent(event, model, option, index)

    def helpEvent(self, event, view, option, index):
        """
        Handle tooltips for the action buttons.
        """
        if index.column() == 7:
            if event.type() == QEvent.Type.ToolTip:
                rect = option.rect
                width = rect.width()
                btn_width = width // 3
                
                # event.pos() in helpEvent is relative to the widget (view)
                # But option.rect is also in view coordinates usually.
                # Let's check click_x relative to rect.
                click_x = event.pos().x()
                local_x = click_x - rect.left()
                
                tooltip = ""
                if local_x < btn_width:
                    tooltip = "Open File"
                elif local_x < btn_width * 2:
                    tooltip = "Open Containing Folder"
                else:
                    # Check ToC status
                    user_data = index.data(Qt.ItemDataRole.UserRole)
                    has_toc = user_data.get('has_toc', False) if user_data else False
                    tooltip = "Open Reader (ToC Ready)" if has_toc else "Generate ToC (Reader)"
                
                if tooltip:
                    QToolTip.showText(event.globalPos(), tooltip, view)
                    return True
        
        return super().helpEvent(event, view, option, index)
