/* ================================================================
   Swipe Handler - Touch gestures for mobile UX
   Enables swipe-to-complete and swipe-to-delete
   ================================================================ */

(function () {
  window.SwipeHandler = class SwipeHandler {
    constructor(container, options = {}) {
      this.container = container;
      this.options = {
        threshold: options.threshold || 80, // Minimum swipe distance
        velocityThreshold: options.velocityThreshold || 0.3,
        onSwipeRight: options.onSwipeRight || null,
        onSwipeLeft: options.onSwipeLeft || null,
        selector: options.selector || '.swipeable-item',
        rightActionColor: options.rightActionColor || '#4CAF50',
        leftActionColor: options.leftActionColor || '#F44336',
        rightActionIcon: options.rightActionIcon || '✓',
        leftActionIcon: options.leftActionIcon || '🗑️',
        ...options
      };

      this.activeElement = null;
      this.startX = 0;
      this.startY = 0;
      this.currentX = 0;
      this.isDragging = false;
      this.startTime = 0;

      this.init();
    }

    init() {
      // Use event delegation for dynamic content
      this.container.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: true });
      this.container.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: false });
      this.container.addEventListener('touchend', this.handleTouchEnd.bind(this));
      this.container.addEventListener('touchcancel', this.handleTouchEnd.bind(this));
    }

    handleTouchStart(e) {
      const target = e.target.closest(this.options.selector);
      if (!target) return;

      this.activeElement = target;
      this.startX = e.touches[0].clientX;
      this.startY = e.touches[0].clientY;
      this.currentX = this.startX;
      this.isDragging = false;
      this.startTime = Date.now();

      // Prepare element for swiping
      this.activeElement.style.transition = 'none';
      this.ensureActionBackgrounds(this.activeElement);
    }

    handleTouchMove(e) {
      if (!this.activeElement) return;

      const currentX = e.touches[0].clientX;
      const currentY = e.touches[0].clientY;
      const deltaX = currentX - this.startX;
      const deltaY = currentY - this.startY;

      // Detect if this is a horizontal swipe (not vertical scroll)
      if (!this.isDragging && Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 10) {
        this.isDragging = true;
        e.preventDefault(); // Prevent scroll
      }

      if (!this.isDragging) return;

      e.preventDefault();
      this.currentX = currentX;

      // Apply transform
      const translateX = deltaX;
      this.activeElement.style.transform = `translateX(${translateX}px)`;

      // Show action backgrounds
      const leftBg = this.activeElement.querySelector('.swipe-action-left');
      const rightBg = this.activeElement.querySelector('.swipe-action-right');

      if (deltaX > 0 && rightBg) {
        // Swiping right
        rightBg.style.opacity = Math.min(deltaX / this.options.threshold, 1);
        if (leftBg) leftBg.style.opacity = 0;
      } else if (deltaX < 0 && leftBg) {
        // Swiping left
        leftBg.style.opacity = Math.min(Math.abs(deltaX) / this.options.threshold, 1);
        if (rightBg) rightBg.style.opacity = 0;
      }
    }

    handleTouchEnd(e) {
      if (!this.activeElement) return;

      const deltaX = this.currentX - this.startX;
      const deltaTime = Date.now() - this.startTime;
      const velocity = Math.abs(deltaX) / deltaTime;

      // Check if swipe threshold is met
      const swipeRight = deltaX > this.options.threshold || (deltaX > 30 && velocity > this.options.velocityThreshold);
      const swipeLeft = deltaX < -this.options.threshold || (deltaX < -30 && velocity > this.options.velocityThreshold);

      if (swipeRight && this.options.onSwipeRight) {
        this.animateAction(this.activeElement, 'right', () => {
          this.options.onSwipeRight(this.activeElement);
        });
      } else if (swipeLeft && this.options.onSwipeLeft) {
        this.animateAction(this.activeElement, 'left', () => {
          this.options.onSwipeLeft(this.activeElement);
        });
      } else {
        // Reset position
        this.resetElement(this.activeElement);
      }

      this.activeElement = null;
      this.isDragging = false;
    }

    ensureActionBackgrounds(element) {
      // Add action background elements if they don't exist
      if (!element.querySelector('.swipe-action-right')) {
        const rightBg = document.createElement('div');
        rightBg.className = 'swipe-action-right';
        rightBg.innerHTML = `<span class="swipe-action-icon">${this.options.rightActionIcon}</span>`;
        element.prepend(rightBg);
      }

      if (!element.querySelector('.swipe-action-left')) {
        const leftBg = document.createElement('div');
        leftBg.className = 'swipe-action-left';
        leftBg.innerHTML = `<span class="swipe-action-icon">${this.options.leftActionIcon}</span>`;
        element.prepend(leftBg);
      }
    }

    animateAction(element, direction, callback) {
      element.style.transition = 'transform 0.3s ease-out, opacity 0.3s ease-out';

      if (direction === 'right') {
        element.style.transform = 'translateX(100%)';
      } else {
        element.style.transform = 'translateX(-100%)';
      }

      element.style.opacity = '0';

      setTimeout(() => {
        callback();
        this.resetElement(element);
      }, 300);
    }

    resetElement(element) {
      if (!element) return;

      element.style.transition = 'transform 0.3s ease-out';
      element.style.transform = 'translateX(0)';
      element.style.opacity = '1';

      // Hide action backgrounds
      const leftBg = element.querySelector('.swipe-action-left');
      const rightBg = element.querySelector('.swipe-action-right');
      if (leftBg) leftBg.style.opacity = 0;
      if (rightBg) rightBg.style.opacity = 0;

      setTimeout(() => {
        element.style.transition = '';
      }, 300);
    }

    destroy() {
      this.container.removeEventListener('touchstart', this.handleTouchStart);
      this.container.removeEventListener('touchmove', this.handleTouchMove);
      this.container.removeEventListener('touchend', this.handleTouchEnd);
      this.container.removeEventListener('touchcancel', this.handleTouchEnd);
    }
  };
})();
