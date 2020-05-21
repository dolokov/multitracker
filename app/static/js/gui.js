function init_gui(){
    let width = 50;
    let height = 200;
    let gui = document.getElementById("gui");
    let stage = new Konva.Stage({
        id: 'stage_gui',
        container: 'container_gui',
        width: width,
        height: height
    });

    document.getElementById("bu_send").onclick = function(){
        let url = "/labeling";
        let package = get_labeling_data();
        if(package !== null){
            post(url,package,redirect_next_task);
        }
    };

    document.getElementById("bu_skip").onclick = function(){
        let url = "/skip_labeling";
        let package = get_skip_data();
        if(package !== null){
            post(url,package,redirect_next_task);
        }
    };

    document.getElementById("bu_skip_keypoint").onclick = function(){
        add_keypoint({x:-100,y:-100});
    };

    update_gui_title();
}

function update_gui_title(){
    document.getElementById('gui_title').innerHTML = "click next point: "+num_indiv.toString()+" - "+keypoint_names[cnt_keypoints];
    document.getElementById('bu_skip_keypoint').innerHTML = "skip point: "+num_indiv.toString()+" - "+keypoint_names[cnt_keypoints];
}