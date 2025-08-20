import * as PIXI from 'pixi.js';

export class MainMenu {
    constructor(app, uiLayer, onStartGame) {
        this.app = app;
        this.onStartGame = onStartGame;
        this.container = new PIXI.Container();
        this.container.visible = false;
        uiLayer.addChild(this.container);

        this.create();
    }

    create() {
        // Create a semi-transparent background
        const background = new PIXI.Graphics();
        background.beginFill(0x000000, 0.8);
        background.drawRect(0, 0, this.app.renderer.width, this.app.renderer.height);
        background.endFill();
        this.container.addChild(background);

        // Title
        const title = new PIXI.Text('Command & Independent Thought', {
            fontFamily: '"Arial Black", Gadget, sans-serif',
            fontSize: 48,
            fill: 0xffd700, // Gold color
            stroke: 0x000000,
            strokeThickness: 4,
            align: 'center'
        });
        title.anchor.set(0.5);
        title.x = this.app.renderer.width / 2;
        title.y = 150;
        this.container.addChild(title);

        // Menu buttons
        const menuItems = ['New Game', 'Load Game', 'Options', 'Exit'];
        const buttonWidth = 300;
        const buttonHeight = 60;
        const startY = 300;
        const spacing = 80;

        menuItems.forEach((item, index) => {
            const button = new PIXI.Graphics();
            button.beginFill(0x333333, 1);
            button.lineStyle(2, 0x888888, 1);
            button.drawRoundedRect(0, 0, buttonWidth, buttonHeight, 10);
            button.endFill();

            const buttonText = new PIXI.Text(item, {
                fontFamily: 'Arial',
                fontSize: 32,
                fill: 0xffffff,
                align: 'center'
            });
            buttonText.anchor.set(0.5);
            buttonText.x = buttonWidth / 2;
            buttonText.y = buttonHeight / 2;

            const buttonContainer = new PIXI.Container();
            buttonContainer.addChild(button);
            buttonContainer.addChild(buttonText);
            buttonContainer.x = (this.app.renderer.width - buttonWidth) / 2;
            buttonContainer.y = startY + index * spacing;

            this.container.addChild(buttonContainer);

            if (item === 'New Game') {
                buttonContainer.eventMode = 'static';
                buttonContainer.cursor = 'pointer';

                buttonContainer.on('pointerdown', this.onStartGame);

                buttonContainer.on('pointerover', () => {
                    button.clear();
                    button.beginFill(0x555555, 1);
                    button.lineStyle(2, 0xaaaaaa, 1);
                    button.drawRoundedRect(0, 0, buttonWidth, buttonHeight, 10);
                    button.endFill();
                });

                buttonContainer.on('pointerout', () => {
                    button.clear();
                    button.beginFill(0x333333, 1);
                    button.lineStyle(2, 0x888888, 1);
                    button.drawRoundedRect(0, 0, buttonWidth, buttonHeight, 10);
                    button.endFill();
                });
            } else {
                // Make other buttons look disabled
                buttonContainer.alpha = 0.5;
            }
        });
    }

    show() {
        this.container.visible = true;
    }

    hide() {
        this.container.visible = false;
    }

    destroy() {
        // The container is a child of the uiLayer, which is managed by the Application.
        // We just need to destroy the container.
        this.container.destroy({ children: true, texture: true, baseTexture: true });
    }
}
