from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush

class AnnotationCanvas(QWidget):
    # 信号: rect(Buffer坐标), is_new_creation
    geometry_changed = pyqtSignal(QRectF, bool) 
    # 信号: 实时鼠标坐标 (x, y)
    mouse_moved_info = pyqtSignal(int, int)
    # 信号: 选中了某个 Event ID
    event_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(800, 500)
        self.setStyleSheet("background-color: #202020;")
        self.setMouseTracking(True)
        
        self.pixmap = None
        self.view_scale = 1.0
        self.view_offset = QPointF(0, 0)
        
        # item结构: (rect, color, label, is_sel, eid)
        self.annotations_to_draw = [] 
        
        self.mode = "IDLE" 
        self.last_mouse_pos = QPointF()
        self.start_pos = QPointF()     
        self.current_rect = QRectF()   
        
        self.active_rect_index = -1    
        self.active_rect_geo = QRectF() 
        
        self.handle_screen_radius = 12 

    def set_image(self, pixmap):
        self.pixmap = pixmap
        self.update()

    def set_annotations(self, annos):
        self.annotations_to_draw = annos
        self.active_rect_index = -1
        self.active_rect_geo = QRectF()
        for i, item in enumerate(annos):
            if item[3]: # is_sel
                self.active_rect_index = i
                self.active_rect_geo = item[0]
                break
        self.update()

    def reset_view(self):
        if not self.pixmap: return
        cw, ch = self.width(), self.height()
        pw, ph = self.pixmap.width(), self.pixmap.height()
        self.view_scale = min(cw/pw, ch/ph) * 0.95
        new_w, new_h = pw * self.view_scale, ph * self.view_scale
        self.view_offset = QPointF((cw - new_w)/2, (ch - new_h)/2)
        self.update()

    def screen_to_buffer(self, pos):
        raw_pos = (pos - self.view_offset) / self.view_scale
        if self.pixmap:
            w = float(self.pixmap.width())
            h = float(self.pixmap.height())
            x = max(0.0, min(raw_pos.x(), w))
            y = max(0.0, min(raw_pos.y(), h))
            return QPointF(x, y)
        return raw_pos

    def get_img_rect(self):
        if self.pixmap:
            return QRectF(0, 0, self.pixmap.width(), self.pixmap.height())
        return QRectF()

    def get_resize_handle(self, rect):
        if self.view_scale <= 0.001: return QRectF()
        buffer_radius = (self.handle_screen_radius + 5) / self.view_scale
        center = rect.bottomRight()
        return QRectF(center.x() - buffer_radius, 
                      center.y() - buffer_radius, 
                      buffer_radius * 2, 
                      buffer_radius * 2)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        if self.pixmap:
            painter.translate(self.view_offset)
            painter.scale(self.view_scale, self.view_scale)
            painter.drawPixmap(0, 0, self.pixmap)

            inv_scale = 1.0 / self.view_scale
            
            # 分离选中和未选中
            unselected_items = []
            selected_item = None

            for item in self.annotations_to_draw:
                if item[3]: # is_sel
                    selected_item = item
                else:
                    unselected_items.append(item)
            
            # 绘制顺序：先未选中，后选中
            draw_queue = unselected_items
            if selected_item:
                draw_queue.append(selected_item)

            for rect, color, label, is_sel, eid in draw_queue:
                draw_rect = self.active_rect_geo if (is_sel and self.mode in ["MOVING", "RESIZING"]) else rect
                
                # A. 绘制边框
                pen_width = 2.0 * inv_scale if is_sel else 1.5 * inv_scale
                style = Qt.PenStyle.SolidLine if is_sel else Qt.PenStyle.DashLine
                painter.setPen(QPen(color, pen_width, style))
                
                brush = QColor(color); brush.setAlpha(40 if is_sel else 0)
                painter.setBrush(QBrush(brush))
                painter.drawRect(draw_rect)
                
                # B. 绘制手柄
                if is_sel:
                    vis_radius = self.handle_screen_radius * inv_scale
                    painter.setPen(QPen(Qt.GlobalColor.white, 2 * inv_scale))
                    painter.setBrush(QBrush(Qt.GlobalColor.cyan))
                    center = draw_rect.bottomRight()
                    handle_rect = QRectF(center.x() - vis_radius, center.y() - vis_radius, 
                                         vis_radius * 2, vis_radius * 2)
                    painter.drawRect(handle_rect)

                # C. 绘制标签 (防止覆盖逻辑)
                painter.save()
                painter.translate(draw_rect.topLeft())
                painter.scale(inv_scale, inv_scale)
                
                font = painter.font(); font.setBold(True); painter.setFont(font)
                fm = painter.fontMetrics()
                text_w = fm.horizontalAdvance(label) + 12
                text_h = fm.height() + 4
                bg_rect = QRectF(0, -text_h, text_w, text_h)
                
                bg_color = QColor(color)
                bg_color.setAlpha(255 if is_sel else 200) 
                painter.fillRect(bg_rect, bg_color)
                
                painter.setPen(Qt.GlobalColor.black)
                painter.drawText(bg_rect, Qt.AlignmentFlag.AlignCenter, label)
                painter.restore()

            if self.mode == "DRAWING":
                painter.setPen(QPen(Qt.GlobalColor.white, 1.0 * inv_scale, Qt.PenStyle.DotLine))
                painter.setBrush(QBrush(QColor(255, 255, 255, 30)))
                painter.drawRect(self.current_rect)

    def mousePressEvent(self, event):
        if not self.pixmap: return
        buf_pos = self.screen_to_buffer(event.position())
        
        if event.button() == Qt.MouseButton.RightButton:
            self.mode = "PANNING"
            self.last_mouse_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        elif event.button() == Qt.MouseButton.LeftButton:
            # 1. 检查是否操作【当前已选中】的框 (调整大小 或 移动)
            # 只有当已经是选中状态时，单击才有效
            if self.active_rect_index != -1:
                # 检查手柄
                if self.get_resize_handle(self.active_rect_geo).contains(buf_pos):
                    self.mode = "RESIZING"; self.start_pos = buf_pos; return
                # 检查内部
                if self.active_rect_geo.contains(buf_pos):
                    self.mode = "MOVING"; self.start_pos = buf_pos; return

            # 2. 如果没点中当前选中的框，或者是点在空白处 -> 直接开始 DRAWING
            # 注意：这里不再循环检查其他未选中的框了，因为那个逻辑移到了双击事件里
            self.mode = "DRAWING"
            self.start_pos = buf_pos
            self.current_rect = QRectF(buf_pos, buf_pos)

    # === 新增：双击事件 (用于选中) ===
    def mouseDoubleClickEvent(self, event):
        if not self.pixmap: return
        if event.button() == Qt.MouseButton.LeftButton:
            buf_pos = self.screen_to_buffer(event.position())
            
            # 倒序遍历（优先选中最上层的框）
            for item in reversed(self.annotations_to_draw):
                rect = item[0]
                eid = item[4]
                if rect.contains(buf_pos):
                    # 发送选中信号
                    self.event_selected.emit(eid)
                    # 可以在这里打印一下调试
                    # print(f"Double Clicked ID: {eid}")
                    return

   
    def mouseMoveEvent(self, event):
        buf_pos = self.screen_to_buffer(event.position())
        self.mouse_moved_info.emit(int(buf_pos.x()), int(buf_pos.y()))
        
        if self.mode == "IDLE":
            # 光标逻辑
            cursor_set = False
            # 1. 优先检测当前选中的框 (Resize/Move)
            if self.active_rect_index != -1:
                if self.get_resize_handle(self.active_rect_geo).contains(buf_pos):
                    self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                    cursor_set = True
                elif self.active_rect_geo.contains(buf_pos):
                    self.setCursor(Qt.CursorShape.SizeAllCursor)
                    cursor_set = True
            
            # 2. 如果没悬停在选中框的操作区，统一设置为手指 (PointingHand)
            # 修改点：无论下面有没有框，都显示为手指，表示“可以点击/画框”
            if not cursor_set:
                self.setCursor(Qt.CursorShape.PointingHandCursor)

        if self.mode == "PANNING":
            delta = event.position() - self.last_mouse_pos
            self.view_offset += delta
            self.last_mouse_pos = event.position()
            self.update()

        elif self.mode == "DRAWING":
            raw_rect = QRectF(self.start_pos, buf_pos).normalized()
            self.current_rect = raw_rect.intersected(self.get_img_rect())
            self.update()

        elif self.mode == "MOVING":
            delta = buf_pos - self.start_pos
            new_geo = self.active_rect_geo.translated(delta)
            img_rect = self.get_img_rect()
            if new_geo.left() < img_rect.left(): new_geo.moveLeft(img_rect.left())
            if new_geo.top() < img_rect.top(): new_geo.moveTop(img_rect.top())
            if new_geo.right() > img_rect.right(): new_geo.moveRight(img_rect.right())
            if new_geo.bottom() > img_rect.bottom(): new_geo.moveBottom(img_rect.bottom())
            self.active_rect_geo = new_geo
            self.start_pos = buf_pos 
            self.update()

        elif self.mode == "RESIZING":
            raw_rect = QRectF(self.active_rect_geo.topLeft(), buf_pos).normalized()
            self.active_rect_geo = raw_rect.intersected(self.get_img_rect())
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.mode = "IDLE"
            # 修改点：右键松开后，光标重置为手指
            self.setCursor(Qt.CursorShape.PointingHandCursor) 
        elif event.button() == Qt.MouseButton.LeftButton:
            if self.mode == "DRAWING":
                if self.current_rect.width() > 2 and self.current_rect.height() > 2:
                    self.geometry_changed.emit(self.current_rect, True)
            elif self.mode in ["MOVING", "RESIZING"]:
                self.geometry_changed.emit(self.active_rect_geo, False)
            
            self.mode = "IDLE"
            self.current_rect = QRectF()
            self.update()
            # 保持状态一致性，操作完成后可以不强制设光标，交给 mouseMoveEvent 更新，
            # 但为了保险起见，这里不需要额外 setCursor(CrossCursor) 了。
   

    def wheelEvent(self, event):
        if not self.pixmap: return
        factor = 1.2 if event.angleDelta().y() > 0 else 1/1.2
        new_scale = self.view_scale * factor
        if 0.01 < new_scale < 50.0:
            mouse = event.position()
            img_pos = (mouse - self.view_offset) / self.view_scale
            self.view_offset = mouse - img_pos * new_scale
            self.view_scale = new_scale
            self.update()