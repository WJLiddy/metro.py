import random
MAP_SIZE = 96
FAR_BOUNDARY_AREA = 5
ARC_RANGE = 8
UPGRADE1_COST = 100
UPGRADE2_COST = 200
# a bad seed can wreck my game for peasant sched - this gives it a fighting chance.
LOW_RES_THRESH = 30

def name():
    return "Metro"

# Metro looks like this.
# Every other doubles up on ranges.

# # # # # # # # # #
# T t t # H h # H h
# t t t # h h # h h
# t t t # H h # H h
# R r r # h h # h h
# r r r # H h # H h
# r r r # h h # H h
# R r r # H h # H h
# r r r # h h # H h
# r r r # # # # # #

# Villagers will go down the path and construct anything that is unconstructed.
# If nothing needs constructed, they will seek out the closest wood or gold.

# To deal with starting position, we transform the world map before and after, so orientation does not matter.

def mirror(x,y,player_idx):
    if(player_idx == 0):
        return [x,y]
    if(player_idx == 1):
        return [MAP_SIZE-1-x,MAP_SIZE-1-y]
    if(player_idx == 2):
        return [MAP_SIZE-1-x,y]
    if(player_idx == 3):
        return [x,MAP_SIZE-1-y]

def negate(x,y,player_idx):
    if(player_idx == 0):
        return [x,y]
    if(player_idx == 1):
        return [-x,-y]
    if(player_idx == 2):
        return [-x,y]
    if(player_idx == 3):
        return [x,-y]

def conv(ws,player_idx):
    convd = [[None for x in range(MAP_SIZE)] for y in range(MAP_SIZE)]
    for x in range(MAP_SIZE):
        for y in range(MAP_SIZE):
            n = mirror(x,y,player_idx)
            convd[n[0]][n[1]] = ws[x][y]
    return convd

def unconv(cmds,player_idx):
    for c in cmds:
        if(c["command"] in ["b","r","s","w","h"]):
            n = mirror(c["arg"][0],c["arg"][1],player_idx)
            # the mirror is close, but we need to top leftify the building too.
            bld_negate = negate(2,2,player_idx)
            if(c["command"] == "h"):
                bld_negate = negate(1,1,player_idx)
            dx = 0
            dy = 0
            if(bld_negate[0] < 0):
                dx = bld_negate[0]
            if(bld_negate[1] < 0):
                dy = bld_negate[1]
            c["arg"] = [n[0] + dx,n[1] + dy]
        if(c["command"] == "m"):
            c["arg"] = negate(c["arg"][0],c["arg"][1],player_idx)


# is oob?
def oob(ws,x,y):
    return x < 0 or x >= MAP_SIZE or y < 0 or y >= MAP_SIZE

# is empty?
def empty(ws,x,y):
    return ws[x][y] is None

# is site empty?
def empty_site(ws,x,y,size):
    for dx in range(size):
        for dy in range(size):
            if(oob(ws,x+dx, y+dy) or not empty(ws,x+dx,y+dy)):
                return False
    return True

# list of adjancent tiles.
def adj(x,y):
    return [[x+1,y],[x,y+1],[x-1,y],[x,y-1],[x+1,y+1],[x-1,y+1],[x-1,y-1],[x+1,y-1]]

# can we afford this?
def can_afford_bld(b,t):
    if(b == "w"):
        return t >= 200
    if(b == "r"):
        return t >= 70 
    if(b == "h"):
        return t >= 30
    return False

# max hp for building.
def max_bld_hp(b):
    if(b == "w"):
        return 80
    if(b == "r"):
        return 60 
    if(b == "h"):
        return 40
    return 0

# return list of my things by category.
def get_units(ws,team_idx):
    vils = []
    mils = []
    blds = []
    for x in range(len(ws)):
        for y in range(len(ws)):
            t = ws[x][y]
            if(t is not None and t != "u" and t["team"] == team_idx):
                if(t["type"] == "v"):
                    vils.append([x,y])
                elif(t["type"] == "a" or t["type"] == "i"):
                    mils.append([x,y])
                else:
                    blds.append([x,y])
    return vils, mils, blds

# return a move to make in order to get adjacent to a tile of type t.
# (used for peasant resources) (only goes down and left.)
def path_to(ws,s_x,s_y,t):
    queue = []
    visited = {}
    
    # vils should never move diagonally in case they miss a buildsite
    for d in [[0,1],[1,0]]:
        # First, we want to preload the queue with the starter directions.
        if((not oob(ws,s_x + d[0], s_y + d[1])) and (empty(ws, s_x + d[0], s_y + d[1]))):
            queue.append((s_x + d[0],s_y + d[1]))
            visited[(s_x + d[0], s_y + d[1])] = d

    # now we have our move options -> see which leads to a destination
    while(len(queue) > 0):
        cur = queue.pop(0)
        
        for d in [[0,1],[1,0],[1,1]]:
            if(not oob(ws,cur[0] + d[0], cur[1] + d[1])):
                # if it's empty, and unvisited, add to queue.
                if(empty(ws,cur[0] + d[0], cur[1] + d[1]) and ((cur[0] + d[0], cur[1] + d[1])) not in visited):
                    visited[(cur[0] + d[0], cur[1] + d[1])] = visited[cur] 
                    queue.append((cur[0] + d[0], cur[1] + d[1]))

                # if it's the target, return.
                if((not empty(ws,cur[0] + d[0], cur[1] + d[1])) and ws[cur[0]+ d[0]][cur[1]+ d[1]] != "u" and ws[cur[0]+ d[0]][cur[1]+ d[1]]["type"] == t):
                    return visited[cur]
    return None

# does this building need repaired?
def needs_fixing(ws,x,y):
    if oob(ws,x,y):
        return False 
    if empty(ws,x,y):
        return False
    # could check for team but also hilarious to fix other people's buildings?
    # can i even fix other people's buildings?
    if (ws[x][y]["type"] in ["w","r","h"] and (ws[x][y]["hp"] < max_bld_hp(ws[x][y]["type"]))):
        return ws[x][y]["id"] 
    return False

# should we start construction on this tile?
def needs_construction(ws,x,y,t):
    if oob(ws,x,y):
        return False 
    if not empty(ws,x,y):
        return False
    
    # this is an empty square in bounds. We should build something!
    local_x = x % 10
    local_y = y % 10
    if(local_x == 1 and local_y == 1 and can_afford_bld("w",t) and empty_site(ws,x,y,3)):
        # don't build a TC if x is odd - favors ranges.
        if(((x-1) % 20) != 0 or ((y-1) % 20) != 0):
            return "r"
        return "w"
    if(local_x == 1 and local_y == 4 and can_afford_bld("r",t) and empty_site(ws,x,y,3)):
        return "r"   
    if(local_x == 1 and local_y == 7 and can_afford_bld("r",t) and empty_site(ws,x,y,3)):
        return "r"   
    
    if(local_x == 5 and local_y == 1 and can_afford_bld("h",t) and empty_site(ws,x,y,2)):
        return "h"
    if(local_x == 5 and local_y == 3 and can_afford_bld("h",t) and empty_site(ws,x,y,2)):
        return "h"
    if(local_x == 5 and local_y == 5 and can_afford_bld("h",t) and empty_site(ws,x,y,2)):
        return "h"
    if(local_x == 5 and local_y == 7 and can_afford_bld("h",t) and empty_site(ws,x,y,2)):
        return "h"

    if(local_x == 8 and local_y == 1 and can_afford_bld("h",t) and empty_site(ws,x,y,2)):
        return "h"
    if(local_x == 8 and local_y == 3 and can_afford_bld("h",t) and empty_site(ws,x,y,2)):
        return "h"
    if(local_x == 8 and local_y == 5 and can_afford_bld("h",t) and empty_site(ws,x,y,2)):
        return "h"
    if(local_x == 8 and local_y == 7 and can_afford_bld("h",t) and empty_site(ws,x,y,2)):
        return "h"
    
    return False

# is there something next to me I can attack?
def should_attack(ws,x,y,team_idx):
    return ((not oob(ws,x,y)) and (not empty(ws,x,y)) and (ws[x][y] != "u") and (ws[x][y]["team"] != team_idx))

# general villager loop.
def vil_ai(ws,x,y,vid,trees,team_idx,res):

    # can i fix the thing next to me?
    fixorder = needs_fixing(ws,x+1,y+1)
    if fixorder != False:
        return {"id":vid,"command":"f","arg":fixorder}

    # can i build the city?
    conorder = needs_construction(ws,x+1,y+1,trees) 
    if conorder != False:
        return {"id":vid,"command":conorder,"arg":[x+1,y+1]}

    # nothing to construct or fix next to me. 
    # can i harvest the resource I was told to harvest?
    for c in adj(x,y):
        if(should_attack(ws,c[0],c[1],team_idx)):
            # attack if enemy OR attack if matches resouces.
            if(ws[c[0]][c[1]]["team"] != -1 or ws[c[0]][c[1]]["type"] == res):
                return {"id":vid,"command":"k","arg":ws[c[0]][c[1]]["id"]}

    # nothing to build or fix or harvest, go looking for resources.
    moveorder = path_to(ws,x,y,res)
    if(moveorder is not None):
        return {"id":vid,"command":"m","arg":moveorder}

    # I can't get to the resource i want, but i also don't want to deal with traffic.
    # so just harvest anything next to me, that is okay.
    for c in adj(x,y):
        # will get non matching resource.
        if(should_attack(ws,c[0],c[1],team_idx)):
            return {"id":vid,"command":"k","arg":ws[c[0]][c[1]]["id"]}

    # I can't do anything useful.
    # So I'm gonna try to just get out of the way and hope i can find it later.
    priority = [[1,1],[1,0],[0,1],[1,-1],[-1,1],[0,-1],[-1,0]]
    random.shuffle(priority)
    for p in priority:
        if((not oob(ws,x+p[0],y+p[1]) and (empty(ws,x+p[0],y+p[1])))):  
            return {"id":vid,"command":"m","arg":[p[0],p[1]]}

    # I'm actually just plain stuck LOL
    return {"id":vid,"command":"m","arg":[1,1]}

# cached archer attack locs.
def archer_deltas():
    out = []
    for dx in range(-ARC_RANGE,ARC_RANGE+1):
        for dy in range(-ARC_RANGE,ARC_RANGE+1):
            if(abs(dx) + abs(dy) <= ARC_RANGE):
                out.append([dx,dy])
    return out

# find valid target.
def target_find(ws,x,y,id,team_idx,ads,tree_only):
    for delt in ads:
        if(not oob(ws,x+delt[0],y+delt[1]) and (not empty(ws,x+delt[0],y+delt[1]))):        
            tile = ws[x+delt[0]][y+delt[1]]
            if(tile != "u" and ((tile["team"] != team_idx and tile["team"] != -1) or (tree_only and tile["type"] == "t"))):
                return {"id":id,"command":"k","arg":tile["id"]}
    return None
      
# just travel to the other side of the map.
def arc_ai(ws,x,y,id,team_idx,ads):
    # find someone to fight
    target = target_find(ws,x,y,id,team_idx,ads,False)
    if(target is not None):
        return target

    # explore other corner. - don't get stuck at edge of map.
    if(x > MAP_SIZE-FAR_BOUNDARY_AREA):
        priority = [[0,-1],[1,-1],[-1,-1]]
        for p in priority:
            if((not oob(ws,x+p[0],y+p[1]) and (empty(ws,x+p[0],y+p[1])))):  
                return {"id":id,"command":"m","arg":[p[0],p[1]]}

    if(y > MAP_SIZE-FAR_BOUNDARY_AREA):
        priority = [[-1,0],[-1,1],[-1,-1]]
        for p in priority:
            if((not oob(ws,x+p[0],y+p[1]) and (empty(ws,x+p[0],y+p[1])))):  
                return {"id":id,"command":"m","arg":[p[0],p[1]]}
    
    # try to diag. if not, try to advance. If not, retreat.
    priority = [[1,1],[1,0],[0,1],[1,-1],[-1,1],[0,-1],[-1,0]]
    for p in priority:
        if((not oob(ws,x+p[0],y+p[1]) and (empty(ws,x+p[0],y+p[1])))):  
            return {"id":id,"command":"m","arg":[p[0],p[1]]}

    # i'm stuck! can i cut down a tree?
    target = target_find(ws,x,y,id,team_idx,ads,True)
    if(target is not None):
        return target

    return {"id":id,"command":"m","arg":[1,1]}

# can i upgrade?
def should_upgrade(players,team_idx):
    up1 = (players[team_idx]["arc_level"] == 1 and players[team_idx]["wood"] > UPGRADE1_COST and players[team_idx]["gold"] > UPGRADE1_COST)
    up2 = (players[team_idx]["arc_level"] == 2 and players[team_idx]["wood"] > UPGRADE2_COST and players[team_idx]["gold"] > UPGRADE2_COST)
    return up1 or up2

def run(world_state,players,team_idx):

    cmds = []

    world_state = conv(world_state,team_idx)

    vils, mils, blds = get_units(world_state,team_idx)

    # villagers roam the streets, then harvest.
    for v in vils:
        u = world_state[v[0]][v[1]]
        # opening - back up to start lol
        if(v[0] == 1 and v[1] == 1):
            cmds.append({"id":u["id"],"command":"m","arg":[-1,-1]})
        else:
            # always get gold if less than 50 in treasury
            # othewise, even split
            res = "g"
            
            # i have enough gold.
            if(players[team_idx]["gold"] > LOW_RES_THRESH):
                if(players[team_idx]["wood"] > LOW_RES_THRESH):
                    # i have enough trees. Split.
                    if((u["id"] % 3) > 0):
                        res = "t"
                else:
                    # we need trees.
                    res = "t"

            cmd = vil_ai(world_state,v[0],v[1],u["id"],players[team_idx]["wood"],team_idx,res)
            cmds.append(cmd)

    # preconstr search array
    ads = archer_deltas()
    for a in mils:
        cmds.append(arc_ai(world_state,a[0],a[1],world_state[a[0]][a[1]]["id"],team_idx,ads))

    # TCs, ranges always produce
    for w in blds:
        if(should_upgrade(players,team_idx)):
            cmds.append({"id":world_state[w[0]][w[1]]["id"],"command":"u","arg":None})
        else:
            cmds.append({"id":world_state[w[0]][w[1]]["id"],"command":"p","arg":None})

    unconv(cmds,team_idx)
    
    return cmds