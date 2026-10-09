"""Contact sheets of actual Blender/Godot captures, with labels; no image synthesis."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'Assets/Characters/BaseHumanoid/Review'
FONT=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',20)
TITLE=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',32)
SMALL=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',17)
def sheet(filename,title,subtitle,entries,columns,width=360,height=480):
    rows=(len(entries)+columns-1)//columns;gap=12;top=100;label=40
    canvas=Image.new('RGB',(columns*width+(columns+1)*gap,top+rows*(height+label+gap)),(23,29,36))
    draw=ImageDraw.Draw(canvas);draw.text((18,12),title,font=TITLE,fill=(226,232,237));draw.text((18,57),subtitle,font=SMALL,fill=(167,183,199))
    for i,(image_name,caption) in enumerate(entries):
        img=Image.open(OUT/image_name).convert('RGB');img.thumbnail((width,height),Image.Resampling.LANCZOS)
        x=gap+(i%columns)*(width+gap);y=top+(i//columns)*(height+label+gap)
        canvas.paste(img,(x+(width-img.width)//2,y+(height-img.height)//2))
        draw.text((x+8,y+height+7),caption,font=FONT,fill=(222,229,237))
    canvas.save(OUT/filename)
sheet('Body_views.png','HUMANOID BASE / BH_01','Actual Blender renders. Male 1.80 m / Female 1.70 m. Neutral A-pose.',
      [(f'{kind}_{view}.png',f'{kind} / {label}') for kind in ['Male','Female'] for view,label in [('front','front'),('side','side'),('back','back'),('quarter','3/4')]],4)
poses=[('arms_forward','arms forward'),('elbow_90','elbow 90'),('overhead','overhead'),('deep_crouch','deep crouch'),('knee_115','knee 115'),('wide_step','wide step')]
sheet('Deformation_tests.png','STATIC SKIN CHECKS','Temporary FK deformation tests. No actions, keyframes or animation clips saved.',
      [(f'{kind}_test_{pose}.png',f'{kind} / {label}') for kind in ['Male','Female'] for pose,label in poses],6,width=260,height=350)
sheet('Topology_and_rig.png','EDITABLE SOURCE / SKIN','53 bones per rig. One connected cage per body. Five independently articulated fingers.',
      [('Skeleton_overlay.png','Blender skeleton overlay'),('Wireframe.png','Editable cage wireframe'),('Male_hand_detail.png','Male hand'),('Female_hand_detail.png','Female hand')],2,width=840,height=560)
print('HUMANOID_CONTACT_SHEETS_DONE')
