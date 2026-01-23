/**
 * Client-side image compression utility
 * Reduces images to max 1MB and 1200px width before upload
 */

const ImageCompressor = {
    MAX_WIDTH: 1200,
    MAX_HEIGHT: 1200,
    MAX_SIZE_MB: 1,
    QUALITY_STEP: 0.05,
    MIN_QUALITY: 0.3,

    /**
     * Compress an image file
     * @param {File} file - The image file to compress
     * @param {Object} options - Optional overrides for MAX_WIDTH, MAX_HEIGHT, MAX_SIZE_MB
     * @returns {Promise<File>} - Compressed image file
     */
    async compress(file, options = {}) {
        const maxWidth = options.maxWidth || this.MAX_WIDTH;
        const maxHeight = options.maxHeight || this.MAX_HEIGHT;
        const maxSizeMB = options.maxSizeMB || this.MAX_SIZE_MB;
        const maxSizeBytes = maxSizeMB * 1024 * 1024;

        // Skip non-image files
        if (!file.type.startsWith('image/')) {
            console.warn('Not an image file:', file.type);
            return file;
        }

        // Skip if already small enough
        if (file.size <= maxSizeBytes) {
            // Still resize if needed
            const img = await this._loadImage(file);
            if (img.width <= maxWidth && img.height <= maxHeight) {
                console.log('Image already optimized:', file.name);
                return file;
            }
        }

        console.log(`Compressing ${file.name}: ${(file.size / 1024 / 1024).toFixed(2)}MB`);

        try {
            const img = await this._loadImage(file);
            const { width, height } = this._calculateDimensions(img, maxWidth, maxHeight);

            // Create canvas and draw resized image
            const canvas = document.createElement('canvas');
            canvas.width = width;
            canvas.height = height;

            const ctx = canvas.getContext('2d');
            ctx.imageSmoothingEnabled = true;
            ctx.imageSmoothingQuality = 'high';
            ctx.drawImage(img, 0, 0, width, height);

            // Compress with decreasing quality until size is acceptable
            let quality = 0.9;
            let blob = await this._canvasToBlob(canvas, file.type, quality);

            while (blob.size > maxSizeBytes && quality > this.MIN_QUALITY) {
                quality -= this.QUALITY_STEP;
                blob = await this._canvasToBlob(canvas, file.type, quality);
                console.log(`Quality ${(quality * 100).toFixed(0)}%: ${(blob.size / 1024 / 1024).toFixed(2)}MB`);
            }

            // If still too large, convert to JPEG (better compression)
            if (blob.size > maxSizeBytes && file.type !== 'image/jpeg') {
                console.log('Switching to JPEG for better compression...');
                quality = 0.85;
                blob = await this._canvasToBlob(canvas, 'image/jpeg', quality);

                while (blob.size > maxSizeBytes && quality > this.MIN_QUALITY) {
                    quality -= this.QUALITY_STEP;
                    blob = await this._canvasToBlob(canvas, 'image/jpeg', quality);
                }
            }

            // Create new file with original name
            const extension = blob.type === 'image/jpeg' ? '.jpg' : this._getExtension(file.name);
            const baseName = file.name.replace(/\.[^/.]+$/, '');
            const newFileName = `${baseName}${extension}`;

            const compressedFile = new File([blob], newFileName, {
                type: blob.type,
                lastModified: Date.now()
            });

            console.log(`Compressed: ${(file.size / 1024 / 1024).toFixed(2)}MB -> ${(compressedFile.size / 1024 / 1024).toFixed(2)}MB`);

            return compressedFile;
        } catch (error) {
            console.error('Compression failed:', error);
            return file; // Return original on error
        }
    },

    /**
     * Compress multiple files
     * @param {FileList|Array<File>} files
     * @param {Object} options
     * @returns {Promise<File[]>}
     */
    async compressMultiple(files, options = {}) {
        const results = [];
        for (const file of files) {
            const compressed = await this.compress(file, options);
            results.push(compressed);
        }
        return results;
    },

    /**
     * Load image from file
     * @private
     */
    _loadImage(file) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.onload = () => {
                URL.revokeObjectURL(img.src);
                resolve(img);
            };
            img.onerror = () => {
                URL.revokeObjectURL(img.src);
                reject(new Error('Failed to load image'));
            };
            img.src = URL.createObjectURL(file);
        });
    },

    /**
     * Calculate new dimensions maintaining aspect ratio
     * @private
     */
    _calculateDimensions(img, maxWidth, maxHeight) {
        let { width, height } = img;

        if (width > maxWidth) {
            height = Math.round(height * (maxWidth / width));
            width = maxWidth;
        }

        if (height > maxHeight) {
            width = Math.round(width * (maxHeight / height));
            height = maxHeight;
        }

        return { width, height };
    },

    /**
     * Convert canvas to blob
     * @private
     */
    _canvasToBlob(canvas, type, quality) {
        return new Promise((resolve) => {
            canvas.toBlob(
                (blob) => resolve(blob),
                type === 'image/png' ? 'image/png' : 'image/jpeg',
                quality
            );
        });
    },

    /**
     * Get file extension
     * @private
     */
    _getExtension(filename) {
        const match = filename.match(/\.[^/.]+$/);
        return match ? match[0] : '.jpg';
    }
};

/**
 * Create a file input handler with automatic compression
 * @param {HTMLInputElement} input - File input element
 * @param {Function} onCompressed - Callback with compressed file(s)
 * @param {Object} options - Compression options
 */
function setupImageCompression(input, onCompressed, options = {}) {
    input.addEventListener('change', async function() {
        if (!this.files || this.files.length === 0) return;

        // Show loading state
        const originalText = this.parentElement?.querySelector('.btn')?.innerHTML;
        const btn = this.parentElement?.querySelector('.btn');
        if (btn) {
            btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Komprimiere...';
            btn.disabled = true;
        }

        try {
            if (this.multiple) {
                const compressed = await ImageCompressor.compressMultiple(this.files, options);
                onCompressed(compressed, this);
            } else {
                const compressed = await ImageCompressor.compress(this.files[0], options);
                onCompressed(compressed, this);
            }
        } catch (error) {
            console.error('Compression error:', error);
            // Fall back to original files
            onCompressed(this.multiple ? Array.from(this.files) : this.files[0], this);
        } finally {
            // Restore button
            if (btn) {
                btn.innerHTML = originalText;
                btn.disabled = false;
            }
        }
    });
}
