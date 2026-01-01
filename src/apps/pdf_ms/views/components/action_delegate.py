from PyQt6.QtWidgets import QStyledItemDelegate, QPushButton, QApplication, QStyle, QStyleOptionButton, QToolTip
from PyQt6.QtCore import Qt, QRect, QSize, pyqtSignal, QEvent
from PyQt6.QtGui import QMouseEvent, QHelpEvent

class ActionDelegate(QStyledItemDelegate):
    """
    Delegate to render buttons in the 'Actions' column.
    """
    
    # Emits row index and action type ('open_file' or 'open_folder')
    action_requested = pyqtSignal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.hover_row = -1
        self.hover_button = -1 # 0 for none, 1 for btn1, 2 for btn2
        
        # Cache icons
        self.icon_file = QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        self.icon_folder = QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)

    def paint(self, painter, option, index):
        if index.column() == 5: # Action Column
            # Calculate rects for two buttons
            rect = option.rect
            width = rect.width()
            height = rect.height()
            
            # Button size
            btn_width = width // 2
            
            # Check Hover State
            is_hovering_cell = (self.hover_row == index.row())
            
            # Button 1: Open File
            btn1_opt = QStyleOptionButton()
            btn1_opt.rect = QRect(rect.left(), rect.top(), btn_width, height)
            btn1_opt.rect.adjust(2, 2, -2, -2) # Padding
            btn1_opt.icon = self.icon_file
            btn1_opt.iconSize = QSize(16, 16)
            btn1_opt.state = QStyle.StateFlag.State_Enabled | QStyle.StateFlag.State_Raised
            if is_hovering_cell and self.hover_button == 1:
                btn1_opt.state |= QStyle.StateFlag.State_MouseOver | QStyle.StateFlag.State_Active
            btn1_opt.toolTip = "Open File"
            
            # Button 2: Open Folder
            btn2_opt = QStyleOptionButton()
            btn2_opt.rect = QRect(rect.left() + btn_width, rect.top(), btn_width, height)
            btn2_opt.rect.adjust(2, 2, -2, -2) # Padding
            btn2_opt.icon = self.icon_folder
            btn2_opt.iconSize = QSize(16, 16)
            btn2_opt.state = QStyle.StateFlag.State_Enabled | QStyle.StateFlag.State_Raised
            if is_hovering_cell and self.hover_button == 2:
                 btn2_opt.state |= QStyle.StateFlag.State_MouseOver | QStyle.StateFlag.State_Active
            btn2_opt.toolTip = "Open Containing Folder"

            style = QApplication.style()
            style.drawControl(QStyle.ControlElement.CE_PushButton, btn1_opt, painter)
            style.drawControl(QStyle.ControlElement.CE_PushButton, btn2_opt, painter)
        else:
            super().paint(painter, option, index)

    def editorEvent(self, event, model, option, index):
        if index.column() == 5:
            if event.type() == QEvent.Type.MouseMove:
                # Track Hover
                rect = option.rect
                width = rect.width()
                btn_width = width // 2
                click_x = event.pos().x()
                
                prev_hover = (self.hover_row, self.hover_button)
                
                # Update State
                current_row = index.row()
                current_btn = 0
                
                if rect.left() <= click_x < rect.left() + btn_width:
                    current_btn = 1
                elif rect.left() + btn_width <= click_x < rect.right():
                    current_btn = 2
                
                self.hover_row = current_row
                self.hover_button = current_btn
                
                if prev_hover != (self.hover_row, self.hover_button):
                     # Force update to repaint
                     view = self.parent()
                     if view:
                         # Update only the specific index
                         view.update(index)
                         
                         # If we moved from one row to another (unlikely in one event, but possible if fast)
                         # we should also update the previous row to clear its hover state
                         if prev_hover[0] != -1 and prev_hover[0] != current_row:
                             prev_index = model.index(prev_hover[0], 5)
                             if prev_index.isValid():
                                 view.update(prev_index)
                return True
                
            elif event.type() == QEvent.Type.Leave:
                 prev_row = self.hover_row
                 self.hover_row = -1
                 self.hover_button = 0
                 view = self.parent()
                 if view and prev_row != -1:
                     prev_index = model.index(prev_row, 5)
                     if prev_index.isValid():
                        view.update(prev_index)

            elif event.type() == QEvent.Type.MouseButtonRelease:
                # Determine which button was clicked
                rect = option.rect
                width = rect.width()
                btn_width = width // 2
                
                click_x = event.pos().x()
                
                if rect.left() <= click_x < rect.left() + btn_width:
                    self.action_requested.emit(index.row(), 'open_file')
                else:
                    self.action_requested.emit(index.row(), 'open_folder')
                return True
            elif event.type() == QEvent.Type.ToolTip:
                 # Show tooltip
                 rect = option.rect
                 width = rect.width()
                 btn_width = width // 2
                 click_x = event.pos().x()
                 
                 tooltip = "Open File" if (rect.left() <= click_x < rect.left() + btn_width) else "Open Containing Folder"
                 QApplication.instance().setOverrideCursor(Qt.CursorShape.ArrowCursor) # Ensure cursor is visible
                 # Note: QToolTip.showText needs global pos. event.globalPos() might be needed but editorEvent takes QEvent.
                 # QHelpEvent has globalPos().
                 if isinstance(event, QHelpEvent):
                     QToolTip.showText(event.globalPos(), tooltip)
                 return True

        return super().editorEvent(event, model, option, index)
