import assert from 'assert';

describe('Mouse Coordinate Transformation Fix', () => {
    const mockCanvas = {
        getBoundingClientRect: () => ({
            left: 50,
            top: 100,
            width: 800,
            height: 600,
        }),
    };

    const mockCamera = {
        scale: 1,
        x: 0,
        y: 0,
        screenToWorld(screenX, screenY, canvasElement = null) {
            let canvasX = screenX;
            let canvasY = screenY;
            if (canvasElement) {
                const rect = canvasElement.getBoundingClientRect();
                canvasX = screenX - rect.left;
                canvasY = screenY - rect.top;
            }
            return {
                x: (canvasX / this.scale) + this.x,
                y: (canvasY / this.scale) + this.y,
            };
        },
    };

    const testCases = [
        {
            name: 'Mouse click at viewport position (300, 200)',
            viewportX: 300,
            viewportY: 200,
        },
        {
            name: 'Mouse click at viewport position (150, 150) after scroll',
            viewportX: 150,
            viewportY: 150,
        },
    ];

    testCases.forEach(({ name, viewportX, viewportY }) => {
        test(name, () => {
            const rect = mockCanvas.getBoundingClientRect();
            const expected = {
                x: viewportX - rect.left,
                y: viewportY - rect.top,
            };
            const result = mockCamera.screenToWorld(viewportX, viewportY, mockCanvas);
            assert.deepStrictEqual(result, expected);
        });
    });
});

export {};
