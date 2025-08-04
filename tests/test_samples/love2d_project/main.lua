-- Love2D 게임 메인 파일
local player = {}
local enemies = {}
local score = 0

function love.load()
    -- 게임 초기화
    love.window.setTitle("Test Love2D Game")
    love.window.setMode(800, 600)
    
    player.x = 400
    player.y = 300
    player.speed = 200
    
    -- 적 생성
    for i = 1, 5 do
        local enemy = {
            x = math.random(0, 800),
            y = math.random(0, 600),
            speed = 100
        }
        table.insert(enemies, enemy)
    end
end

function love.update(dt)
    -- 플레이어 이동
    if love.keyboard.isDown("left") then
        player.x = player.x - player.speed * dt
    end
    if love.keyboard.isDown("right") then
        player.x = player.x + player.speed * dt
    end
    if love.keyboard.isDown("up") then
        player.y = player.y - player.speed * dt
    end
    if love.keyboard.isDown("down") then
        player.y = player.y + player.speed * dt
    end
    
    -- 적 이동
    for i, enemy in ipairs(enemies) do
        enemy.x = enemy.x + enemy.speed * dt
        if enemy.x > 800 then
            enemy.x = -50
        end
    end
end

function love.draw()
    -- 플레이어 그리기
    love.graphics.setColor(0, 1, 0)
    love.graphics.rectangle("fill", player.x, player.y, 50, 50)
    
    -- 적 그리기
    love.graphics.setColor(1, 0, 0)
    for i, enemy in ipairs(enemies) do
        love.graphics.rectangle("fill", enemy.x, enemy.y, 30, 30)
    end
    
    -- 점수 표시
    love.graphics.setColor(1, 1, 1)
    love.graphics.print("Score: " .. score, 10, 10)
end

function love.keypressed(key)
    if key == "space" then
        score = score + 1
    end
    if key == "escape" then
        love.event.quit()
    end
end