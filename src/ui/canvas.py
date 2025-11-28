from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush

class AnnotationCanvas(QWidget):
    # 信号: rect(Buffer坐标), is_new_creation
    geometry_changed = pyqtSignal(QRectF, bool) 
    # 信号: 实时鼠标坐标 (x, y)
    mouse_moved_info = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(800, 500)
        self.setStyleSheet("background-color: #202020;")
        self.setMouseTracking(True)
        
        self.pixmap = None
        self.view_scale = 1.0
        self.view_offset = QPointF(0, 0)
        self.annotations_to_draw = [] 
        
        self.mode = "IDLE" 
        self.last_mouse_pos = QPointF()
        self.start_pos = QPointF()     
        self.current_rect = QRectF()   
        
        self.active_rect_index = -1    
        self.active_rect_geo = QRectF() 
        
        # === 修改 1: 定义手柄在屏幕上的半径 (像素) ===
        # 无论图片缩放多少倍，鼠标感应半径始终是 12px (直径 24px)
        self.handle_screen_radius = 12 

    def set_image(self, pixmap):
        self.pixmap = pixmap
        self.update()

    def set_annotations(self, annos):
        self.annotations_to_draw = annos
        self.active_rect_index = -1
        self.active_rect_geo = QRectF()
        for i, (rect, _, _, is_sel) in enumerate(annos):
            if is_sel:
                self.active_rect_index = i
                self.active_rect_geo = rect
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
        """将屏幕坐标转换为图片坐标，并强制限制在图片范围内"""
        # 1. 算出原始映射坐标
        raw_pos = (pos - self.view_offset) / self.view_scale
        
        # 2. 强制限制在图像范围内 (Clamp)
        if self.pixmap:
            w = float(self.pixmap.width())
            h = float(self.pixmap.height())
            x = max(0.0, min(raw_pos.x(), w))
            y = max(0.0, min(raw_pos.y(), h))
            return QPointF(x, y)
        return raw_pos

    def get_img_rect(self):
        """获取图片自身的矩形边界 (0,0,w,h)"""
        if self.pixmap:
            return QRectF(0, 0, self.pixmap.width(), self.pixmap.height())
        return QRectF()

    def get_resize_handle(self, rect):
        """
        === 修改 2: 动态计算手柄判定区域 ===
        根据当前的缩放比例，反向计算出在 Image 坐标系下，
        需要多大的区域才能对应屏幕上的 12+5 像素。
        """
        if self.view_scale <= 0.001: return QRectF()
        
        # 屏幕像素 / 缩放比例 = 图片像素
        # +5 是为了增加一点容错，让感应区域比视觉区域稍微大一点点
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
            
            for i, (rect, color, label, is_sel) in enumerate(self.annotations_to_draw):
                draw_rect = self.active_rect_geo if (is_sel and self.mode in ["MOVING", "RESIZING"]) else rect
                
                pen_width = 2.0 * inv_scale if is_sel else 1.5 * inv_scale
                style = Qt.PenStyle.SolidLine if is_sel else Qt.PenStyle.DashLine
                painter.setPen(QPen(color, pen_width, style))
                
                brush = QColor(color); brush.setAlpha(40 if is_sel else 0)
                painter.setBrush(QBrush(brush))
                painter.drawRect(draw_rect)
                
                if is_sel:
                    # === 修改 3: 绘制大小固定的手柄 ===
                    # 计算在当前缩放比例下，屏幕上的 handle_screen_radius 对应多少图片像素
                    vis_radius = self.handle_screen_radius * inv_scale
                    
                    painter.setPen(QPen(Qt.GlobalColor.white, 2 * inv_scale))
                    painter.setBrush(QBrush(Qt.GlobalColor.cyan))
                    
                    center = draw_rect.bottomRight()
                    # 绘制方块
                    handle_rect = QRectF(center.x() - vis_radius, 
                                         center.y() - vis_radius, 
                                         vis_radius * 2, 
                                         vis_radius * 2)
                    painter.drawRect(handle_rect)

                painter.save()
                painter.translate(draw_rect.topLeft())
                painter.scale(inv_scale, inv_scale)
                font = painter.font(); font.setBold(True); painter.setFont(font)
                bg = QRectF(0, -22, max(60, len(label)*12), 20)
                painter.fillRect(bg, color)
                painter.setPen(Qt.GlobalColor.black)
                painter.drawText(bg, Qt.AlignmentFlag.AlignCenter, label)
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
        elif event.button() == Qt.MouseButton.LeftButton:
            if self.active_rect_index != -1:
                # 优先检查调整手柄
                if self.get_resize_handle(self.active_rect_geo).contains(buf_pos):
                    self.mode = "RESIZING"; self.start_pos = buf_pos; return
                # 其次检查移动
                if self.active_rect_geo.contains(buf_pos):
                    self.mode = "MOVING"; self.start_pos = buf_pos; return

            # 如果都没选中，开始画新框
            self.mode = "DRAWING"
            self.start_pos = buf_pos
            self.current_rect = QRectF(buf_pos, buf_pos)

    def mouseMoveEvent(self, event):
        buf_pos = self.screen_to_buffer(event.position())
        
        # 实时发送坐标
        self.mouse_moved_info.emit(int(buf_pos.x()), int(buf_pos.y()))
        
        # 鼠标悬停时的光标样式处理
        if self.mode == "IDLE" and self.active_rect_index != -1:
            if self.get_resize_handle(self.active_rect_geo).contains(buf_pos):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor) # 对角线拉伸光标
            elif self.active_rect_geo.contains(buf_pos):
                self.setCursor(Qt.CursorShape.SizeAllCursor)   # 移动光标
            else:
                self.setCursor(Qt.CursorShape.CrossCursor)     # 十字光标

        if self.mode == "PANNING":
            delta = event.position() - self.last_mouse_pos
            self.view_offset += delta
            self.last_mouse_pos = event.position()
            self.update()

        elif self.mode == "DRAWING":
            # === 修复: 取交集，确保绝不画出界 ===
            raw_rect = QRectF(self.start_pos, buf_pos).normalized()
            self.current_rect = raw_rect.intersected(self.get_img_rect())
            self.update()

        elif self.mode == "MOVING":
            delta = buf_pos - self.start_pos
            new_geo = self.active_rect_geo.translated(delta)
            
            # === 修复: 如果移动后的框超出了边界，强制推回来 ===
            img_rect = self.get_img_rect()
            if new_geo.left() < img_rect.left(): new_geo.moveLeft(img_rect.left())
            if new_geo.top() < img_rect.top(): new_geo.moveTop(img_rect.top())
            if new_geo.right() > img_rect.right(): new_geo.moveRight(img_rect.right())
            if new_geo.bottom() > img_rect.bottom(): new_geo.moveBottom(img_rect.bottom())
            
            self.active_rect_geo = new_geo
            # 重置 start_pos，避免累积误差
            self.start_pos = buf_pos 
            self.update()

        elif self.mode == "RESIZING":
            # === 修复: 取交集，确保绝不拉出界 ===
            raw_rect = QRectF(self.active_rect_geo.topLeft(), buf_pos).normalized()
            self.active_rect_geo = raw_rect.intersected(self.get_img_rect())
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.mode = "IDLE"
            self.setCursor(Qt.CursorShape.CrossCursor)
        elif event.button() == Qt.MouseButton.LeftButton:
            if self.mode == "DRAWING":
                if self.current_rect.width() > 2 and self.current_rect.height() > 2:
                    self.geometry_changed.emit(self.current_rect, True)
            elif self.mode in ["MOVING", "RESIZING"]:
                self.geometry_changed.emit(self.active_rect_geo, False)
            
            self.mode = "IDLE"
            self.current_rect = QRectF()
            self.update()

    def wheelEvent(self, event):
        if not self.pixmap: return
        factor = 1.2 if event.angleDelta().y() > 0 else 1/1.2
        new_scale = self.view_scale * factor
        # 限制缩放范围
        if 0.01 < new_scale < 50.0:
            mouse = event.position()
            img_pos = (mouse - self.view_offset) / self.view_scale
            self.view_offset = mouse - img_pos * new_scale
            self.view_scale = new_scale
            self.update()